"""Operational nowcasting: live METAR retrieval -> identical feature pipeline -> calibrated
probabilities, ILS/RVR category probabilities, alert level and SHAP explanations.

The functions here are used by the web application, the live logger and the operational
replay (scripts/08_operational_replay.py) so that offline and online predictions are
produced by exactly the same code.
"""
from __future__ import annotations

import csv
import io
import math
import urllib.request
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd

from .config import MODELS, STATION, VIS_FOG_M
from .dataset import decode, quality_control
from .features import build_grid, feature_matrix, make_features
from .labels import FACTOR_OF
from .metar import parse_metar
from .metrics import rvr_class_probs

UA = "Mozilla/5.0 (LTAC fog nowcasting research app)"
# 7 days of reports: the features need MEMORY_H = 96 h, the rest lets the live cycle recompute
# skipped issue times (live_log.catch_up). AWC returns at most 400 reports, about 8 days at LTAC.
HISTORY_H = 168


# ============================================================================ retrieval
def _get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_awc(hours: int = HISTORY_H, now: datetime | None = None) -> pd.DataFrame:
    now = now or datetime.now(timezone.utc)
    txt = _get(f"https://aviationweather.gov/api/data/metar?ids={STATION}&format=raw&hours={hours}")
    rows = []
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = parse_metar(line, now)
        if rec.obs_time is not None:
            rows.append((pd.Timestamp(rec.obs_time), line, "AWC", rec.report_type))
    return pd.DataFrame(rows, columns=["obs_time", "raw", "source", "type_hint"])


def fetch_iem(hours: int = HISTORY_H, now: datetime | None = None) -> pd.DataFrame:
    now = now or datetime.now(timezone.utc)
    s, e = now - timedelta(hours=hours), now + timedelta(days=1)
    url = ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?"
           f"station={STATION}&data=metar&year1={s.year}&month1={s.month}&day1={s.day}"
           f"&year2={e.year}&month2={e.month}&day2={e.day}&tz=Etc/UTC&format=onlycomma"
           "&latlon=no&missing=M&trace=T&direct=no&report_type=3&report_type=4")
    rows = []
    for r in csv.DictReader(io.StringIO(_get(url, timeout=60))):
        t = pd.Timestamp(r["valid"], tz="UTC")
        if t >= pd.Timestamp(s):
            rows.append((t, r["metar"], "IEM", None))
    return pd.DataFrame(rows, columns=["obs_time", "raw", "source", "type_hint"])


def fetch_reports(hours: int = HISTORY_H) -> tuple[pd.DataFrame, str]:
    """Latest reports from AWC; falls back to IEM when AWC is unreachable."""
    errors = []
    for name, fn in (("aviationweather.gov", fetch_awc), ("IEM", fetch_iem)):
        try:
            df = fn(hours)
            if len(df):
                return df.drop_duplicates("obs_time").sort_values("obs_time"), name
        except Exception as exc:  # network errors -> try the next source
            errors.append(f"{name}: {exc!r}")
    raise RuntimeError("no METAR source reachable: " + "; ".join(errors))


# ============================================================================ models
class Nowcaster:
    """Loads the deployed LightGBM models (+ calibrators, thresholds, SHAP explainers)."""

    def __init__(self, model_name: str = "lgbm"):
        import shap

        self.models = {}
        for target in ("fog", "rvr550", "rvr350"):
            for h in range(1, 7):
                f = MODELS / f"tab_{model_name}_{target}_{h}h.joblib"
                if f.exists():
                    # joblib/pickle: only model files produced by our own training scripts
                    self.models[(target, h)] = joblib.load(f)
        if not self.models:
            raise FileNotFoundError("no trained models found in models/")
        self.explainers = {k: shap.TreeExplainer(m.model.booster_)
                           for k, m in self.models.items() if k[0] == "fog"}

    @property
    def fog_horizons(self) -> list[int]:
        return sorted(h for (t, h) in self.models if t == "fog")

    @property
    def rvr_horizons(self) -> list[int]:
        return sorted(h for (t, h) in self.models if t == "rvr350"
                      and ("rvr550", h) in self.models)

    # ----------------------------------------------------------------------
    def features_from_reports(self, reports: pd.DataFrame, at: pd.Timestamp | None = None):
        dec = decode(reports.reset_index(drop=True))
        clean, _ = quality_control(dec)
        start = clean["obs_time"].min().floor("h")
        grid = build_grid(clean, start=start, end=at)
        base = make_features(grid)
        return grid, base, clean

    def predict_at(self, base: pd.DataFrame, t: pd.Timestamp, explain: bool = True,
                   top_k: int = 8) -> dict:
        out = {"fog": {}, "rvr": {}, "shap": {}, "factors": {}}
        row = base.loc[[t]]
        Xs = {h: feature_matrix(None, h, base=row) for h in {h for (_, h) in self.models}}
        for h in self.fog_horizons:
            fm = self.models[("fog", h)]
            X = Xs[h]
            p = float(fm.predict(X)[0])
            out["fog"][h] = {"p": p, "threshold": fm.threshold, "warn": p >= fm.threshold}
            if explain:
                sv = self.explainers[("fog", h)].shap_values(X[fm.features])
                sv = np.asarray(sv[1] if isinstance(sv, list) else sv)[0]
                order = np.argsort(-np.abs(sv))[:top_k]
                out["shap"][h] = [{"feature": fm.features[i], "value": float(sv[i]),
                                   "x": None if pd.isna(X[fm.features[i]].iloc[0])
                                   else float(X[fm.features[i]].iloc[0])} for i in order]
                groups: dict[str, float] = {}
                for f, v in zip(fm.features, sv):
                    g = FACTOR_OF.get(f, "report")
                    groups[g] = groups.get(g, 0.0) + float(v)
                out["factors"][h] = sorted(({"group": g, "value": v} for g, v in groups.items()),
                                           key=lambda d: -abs(d["value"]))
        for h in self.rvr_horizons:
            X = Xs[h]
            p550 = float(self.models[("rvr550", h)].predict(X)[0])
            p350 = float(self.models[("rvr350", h)].predict(X)[0])
            probs = rvr_class_probs(np.array([p550]), np.array([p350]))[0]
            out["rvr"][h] = {"p_cat1": float(probs[0]), "p_cat2": float(probs[1]),
                             "p_cat3": float(probs[2]), "p_lt550": p550, "p_lt350": p350}
        return out


# ============================================================================ alerting
ALERT_LEVELS = ["green", "yellow", "orange", "red"]


def alert_level(fog: dict, fog_now: bool) -> str:
    """Operational alert tier from calibrated probabilities.

    r_h = p_h / tau_h, where tau_h is the validation-optimal (max-CSI) threshold of the
    h-hour model. RED: fog observed now or expected within 2 h (r >= 1 for h <= 2);
    ORANGE: fog expected in 3-6 h (r >= 1 for h >= 3); YELLOW: elevated risk (r >= 0.5);
    GREEN otherwise.
    """
    ratio = {h: v["p"] / max(v["threshold"], 1e-6) for h, v in fog.items()}
    if fog_now or any(r >= 1 for h, r in ratio.items() if h <= 2):
        return "red"
    if any(r >= 1 for h, r in ratio.items() if h >= 3):
        return "orange"
    if any(r >= 0.5 for r in ratio.values()):
        return "yellow"
    return "green"


def current_conditions(grid: pd.DataFrame, clean: pd.DataFrame, t: pd.Timestamp) -> dict:
    row = grid.loc[t]
    last = clean[clean["obs_time"] <= t].iloc[-1]

    def num(x):
        return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else float(x)

    return {
        "obs_time": last["obs_time"].isoformat(), "raw": last["raw"],
        "report_type": last["report_type"],
        "vis_m": num(row["vis_m"]), "rvr_min_m": num(row["rvr_min_m"]),
        "temp_c": num(row["temp_c"]), "dewpt_c": num(row["dewpt_c"]),
        "dpd_c": num(row["dpd_c"]), "rh_pct": num(row["rh_pct"]),
        "wind_dir": num(row["wind_dir"]), "wind_speed_kt": num(row["wind_speed_kt"]),
        "qnh_hpa": num(row["qnh_hpa"]), "ceiling_ft": num(row["ceiling_ft"]),
        "wx": last["wx"], "fog_now": bool(row["vis_m"] < VIS_FOG_M) if num(row["vis_m"]) is not None else False,
    }


def run_nowcast(nc: Nowcaster, reports: pd.DataFrame | None = None, source: str = "",
                prepared: tuple | None = None) -> dict:
    """Full live cycle: fetch -> features -> probabilities -> alert -> explanation.
    ``prepared`` = (grid, base, clean) avoids recomputing features."""
    if prepared is None:
        if reports is None:
            reports, source = fetch_reports()
        prepared = nc.features_from_reports(reports)
    grid, base, clean = prepared
    valid = base.index[grid["vis_m"].notna().to_numpy()]
    t = valid[-1]
    pred = nc.predict_at(base, t)
    cond = current_conditions(grid, clean, t)
    hist = grid.loc[grid.index >= t - pd.Timedelta(hours=48), ["vis_m", "rvr_min_m"]]
    return {
        "station": STATION, "issue_time": t.isoformat(), "source": source,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conditions": cond, "fog": pred["fog"], "rvr": pred["rvr"], "shap": pred["shap"],
        "factors": pred["factors"],
        "alert": alert_level(pred["fog"], cond["fog_now"]),
        "history": [{"t": i.isoformat(), "vis_m": None if pd.isna(v) else float(v),
                     "rvr_m": None if pd.isna(r) else float(r)}
                    for i, v, r in zip(hist.index, hist["vis_m"], hist["rvr_min_m"])],
    }
