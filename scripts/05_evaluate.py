"""Step 5 – verification of all models against persistence, climatology, METAR TREND and TAF.

Outputs (results/tables): scores_<split>.csv, bootstrap_test.csv, paired_tests.csv,
trend_comparison.csv, taf_comparison.csv, onset_dissipation.csv, rvr_multiclass.csv,
per_season.csv, leadtime_curve.csv; plus results/metrics.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.baselines import load_taf_archive, taf_forecasts, trend_forecasts, vis_to_event  # noqa: E402
from esenboga.config import (COLD_SEASON_MONTHS, HORIZONS, HORIZONS_ALL, MODELS,  # noqa: E402
                             PROCESSED, RESULTS, RVR_CAT_I_M, RVR_CAT_II_M, TABLES)
from esenboga.data import climatology, fog_season  # noqa: E402
from esenboga.metrics import (brier, categorical_scores, multiclass_scores,  # noqa: E402
                              probabilistic_scores, rvr_class_probs)

PRED_DIR = RESULTS / "predictions"
TAB = ["lr", "rf", "xgb", "lgbm"]
DEEP = ["gru", "lstm"]
RNG = np.random.default_rng(2026)


# ============================================================================ loading
def load_task(target: str, h: int) -> tuple[pd.DataFrame, dict]:
    # joblib (pickle) is only used for model files written by our own training scripts
    pred = pd.read_parquet(PRED_DIR / f"pred_{target}_{h}h.parquet")
    thr = {}
    for m in TAB:
        f = MODELS / f"tab_{m}_{target}_{h}h.joblib"
        if f.exists() and m in pred:
            thr[m] = joblib.load(f).threshold
    for c in DEEP:
        f, b = PRED_DIR / f"deep_{c}.parquet", MODELS / f"deep_{c}.joblib"
        key = f"{target}_{h}h"
        if f.exists() and b.exists() and key in pq.read_schema(f).names:
            d = pd.read_parquet(f, columns=[key, key + "_raw"])
            pred[c] = d[key].reindex(pred.index)
            pred[c + "_raw"] = d[key + "_raw"].reindex(pred.index)
            thr[c] = joblib.load(b)["thresholds"][key]
    return pred, thr


# ============================================================================ bootstrap
def _day_codes(index: pd.DatetimeIndex) -> np.ndarray:
    return pd.factorize(index.floor("D"))[0]


def cat_counts_by_day(y, yhat, days, n_days):
    y, yhat = y.astype(bool), yhat.astype(bool)
    return np.stack([np.bincount(days, weights=(yhat & y), minlength=n_days),
                     np.bincount(days, weights=(yhat & ~y), minlength=n_days),
                     np.bincount(days, weights=(~yhat & y), minlength=n_days),
                     np.bincount(days, weights=(~yhat & ~y), minlength=n_days)])


def scores_from_counts(a, b, c, d):
    with np.errstate(divide="ignore", invalid="ignore"):
        csi = a / (a + b + c)
        hss = 2 * (a * d - b * c) / ((a + c) * (c + d) + (a + b) * (b + d))
        pod = a / (a + c)
        far = b / (a + b)
    return {"CSI": csi, "HSS": hss, "POD": pod, "FAR": far}


def bootstrap_categorical(forecasts: dict, y, days, n_boot=2000):
    """Paired day-block bootstrap for several deterministic forecasts at once."""
    n_days = days.max() + 1
    picks = RNG.integers(0, n_days, size=(n_boot, n_days))
    W = np.stack([np.bincount(p, minlength=n_days) for p in picks])      # (n_boot, n_days)
    out = {}
    for name, yhat in forecasts.items():
        cnt = cat_counts_by_day(y, yhat, days, n_days)                    # (4, n_days)
        sums = W @ cnt.T                                                   # (n_boot, 4)
        out[name] = scores_from_counts(*sums.T)
    return out


def bootstrap_prob(y, p, clim, days, n_boot=300):
    n_days = days.max() + 1
    idx_by_day = np.split(np.argsort(days, kind="stable"), np.cumsum(np.bincount(days))[:-1])
    aps, bsss = [], []
    for _ in range(n_boot):
        pick = RNG.integers(0, n_days, n_days)
        idx = np.concatenate([idx_by_day[k] for k in pick])
        yy = y[idx]
        if yy.sum() == 0:
            continue
        aps.append(average_precision_score(yy, p[idx]))
        bsss.append(1 - brier(yy, p[idx]) / brier(yy, clim[idx]))
    return np.asarray(aps), np.asarray(bsss)


def ci(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return (float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))) if len(x) else (np.nan, np.nan)


# ============================================================================ main blocks
def score_table(pred, thr, y, mask, clim, persistence, extra_det=None):
    rows = []
    for m in [c for c in TAB + DEEP if c in pred]:
        p = pred[m].to_numpy()[mask]
        ok = ~np.isnan(p)
        ps = probabilistic_scores(y[ok], p[ok], clim[ok])
        cs = categorical_scores(y[ok], p[ok] >= thr[m])
        rows.append({"model": m, "kind": "ML", "threshold": thr[m], **ps, **cs})
    dets = {"persistence": persistence[mask]}
    dets.update({k: v[mask] for k, v in (extra_det or {}).items()})
    for name, yhat in dets.items():
        ok = ~np.isnan(yhat)
        if not ok.any():
            continue
        cs = categorical_scores(y[ok], yhat[ok] == 1)
        bs = brier(y[ok], yhat[ok])
        rows.append({"model": name, "kind": "baseline", "n": int(ok.sum()),
                     "base_rate": float(y[ok].mean()), "Brier": bs,
                     "BSS": 1 - bs / brier(y[ok], clim[ok]), **cs})
    return rows


def onset_dissipation(feats, pred_by_h, thr_by_h, split_name="test"):
    """Hit rates for fog onsets/dissipations forecast h hours ahead."""
    fog = feats["fog_now"]
    prev4 = pd.concat([fog.shift(k) for k in range(1, 5)], axis=1)
    onset = (fog == 1) & (prev4 == 0).all(axis=1)
    prev2 = pd.concat([fog.shift(k) for k in range(1, 3)], axis=1)
    dissip = (fog == 0) & (prev2 == 1).all(axis=1)
    rows = []
    for kind, ev in (("onset", onset), ("dissipation", dissip)):
        times = ev[ev].index
        for h, pred in pred_by_h.items():
            issue = times - pd.Timedelta(hours=h)
            sub = pred.reindex(issue)
            keep = (sub["split"] == split_name).to_numpy()
            if keep.sum() == 0:
                continue
            sub = sub[keep]
            want = 1 if kind == "onset" else 0
            row = {"event": kind, "h": h, "n_events": int(keep.sum())}
            for m in [c for c in TAB + DEEP if c in sub]:
                yhat = (sub[m] >= thr_by_h[h][m]).astype(int)
                row[m] = float((yhat == want).mean())
            pers = feats["fog_now"].reindex(sub.index)
            row["persistence"] = float((pers == want).mean())
            rows.append(row)
    return rows


def main() -> None:
    feats = pd.read_parquet(PROCESSED / "features.parquet")
    targ = pd.read_parquet(PROCESSED / "targets.parquet")
    taf_arch = load_taf_archive()
    print(f"TAF archive: {len(taf_arch.tafs)} TAFs", flush=True)
    all_rows, boot_rows, paired_rows, trend_rows, taf_rows, season_rows = [], [], [], [], [], []
    rvr_rows, lead_rows = [], []
    pred_fog_by_h, thr_fog_by_h = {}, {}
    summary = {}

    horizons = [h for h in HORIZONS_ALL if (PRED_DIR / f"pred_fog_{h}h.parquet").exists()]
    for target in ("fog", "rvr550", "rvr350"):
        for h in horizons:
            f = PRED_DIR / f"pred_{target}_{h}h.parquet"
            if not f.exists():
                continue
            pred, thr = load_task(target, h)
            idx = pred.index
            y_all = pred["y"].to_numpy().astype(float)
            split = pred["split"].to_numpy()
            tr = split == "train"
            clim_all = climatology(idx[tr], y_all[tr], idx, h)
            if target == "fog":
                pers = feats["fog_now"].reindex(idx).to_numpy()
            else:
                lim = RVR_CAT_I_M if target == "rvr550" else RVR_CAT_II_M
                r = feats["rvr_eff_m"].reindex(idx).to_numpy()
                pers = np.where(np.isnan(r), np.nan, (r < lim).astype(float))
            extra = {}
            if target == "fog" and h <= 2:
                tf = trend_forecasts(idx, h)
                extra["trend_prev"] = vis_to_event(tf["trend_vis_prev"])
                extra["trend_worst"] = vis_to_event(tf["trend_vis_worst"])
            if target == "fog":
                tafs = taf_forecasts(idx, h, taf_arch)
                extra["taf_prev"] = vis_to_event(tafs["taf_vis_prev"])
                extra["taf_worst"] = vis_to_event(tafs["taf_vis_worst"])
            if target == "fog":
                pred_fog_by_h[h], thr_fog_by_h[h] = pred, thr
            cold = np.isin(idx.month, COLD_SEASON_MONTHS)
            for part in ("val", "test", "live"):
                for season_sel, label in ((np.ones(len(idx), bool), "all"), (cold, "cold")):
                    mask = (split == part) & season_sel
                    if mask.sum() == 0 or y_all[mask].sum() == 0:
                        continue
                    ext = {k: v for k, v in extra.items() if not k.startswith("taf")}
                    for r_ in score_table(pred, thr, y_all[mask], mask, clim_all[mask], pers, ext):
                        all_rows.append({"target": target, "h": h, "split": part,
                                         "season": label, **r_})
            if h not in HORIZONS:
                # lead-time curve only needs LightGBM + persistence on test
                m = split == "test"
                for name, yhat in (("lgbm", pred["lgbm"].to_numpy()[m] >= thr["lgbm"]),
                                   ("persistence", pers[m] == 1)):
                    lead_rows.append({"target": target, "h": h, "model": name,
                                      **categorical_scores(y_all[m], yhat)})
                continue
            m = split == "test"
            for name in ("lgbm", "persistence"):
                yhat = (pred["lgbm"].to_numpy()[m] >= thr["lgbm"]) if name == "lgbm" else pers[m] == 1
                lead_rows.append({"target": target, "h": h, "model": name,
                                  **categorical_scores(y_all[m], yhat)})

            # --------------------------------------------------------- bootstrap (test)
            yt = y_all[m].astype(int)
            days = _day_codes(idx[m])
            dets = {mm: (pred[mm].to_numpy()[m] >= thr[mm]).astype(int)
                    for mm in TAB + DEEP if mm in pred}
            dets["persistence"] = np.nan_to_num(pers[m]).astype(int)
            bs = bootstrap_categorical(dets, yt, days)
            for name, d in bs.items():
                row = {"target": target, "h": h, "model": name}
                for k, v in d.items():
                    row[f"{k}_lo"], row[f"{k}_hi"] = ci(v)
                if name in TAB + DEEP and target == "fog":
                    aps, bsss = bootstrap_prob(yt, pred[name].to_numpy()[m], clim_all[m], days)
                    row["PR_AUC_lo"], row["PR_AUC_hi"] = ci(aps)
                    row["BSS_lo"], row["BSS_hi"] = ci(bsss)
                boot_rows.append(row)
            for mm in [c for c in TAB + DEEP if c in pred]:
                for metric in ("CSI", "HSS"):
                    diff = bs[mm][metric] - bs["persistence"][metric]
                    lo, hi = ci(diff)
                    paired_rows.append({"target": target, "h": h, "model": mm,
                                        "vs": "persistence", "metric": metric,
                                        "diff_mean": float(np.nanmean(diff)), "lo": lo, "hi": hi,
                                        "significant": bool(lo > 0 or hi < 0)})

            # --------------------------------------------------------- TREND / TAF (fog)
            for key, rows_out in (("trend", trend_rows), ("taf", taf_rows)):
                if f"{key}_prev" not in extra:
                    continue
                for part in ("test", "live", "val"):
                    sel = (split == part) & ~np.isnan(extra[f"{key}_prev"])
                    if sel.sum() == 0 or y_all[sel].sum() == 0:
                        continue
                    yy = y_all[sel]
                    base = {"target": target, "h": h, "split": part, "n": int(sel.sum()),
                            "events": int(yy.sum())}
                    for name in [c for c in TAB + DEEP if c in pred]:
                        rows_out.append({**base, "forecast": name, **categorical_scores(
                            yy, pred[name].to_numpy()[sel] >= thr[name])})
                    rows_out.append({**base, "forecast": "persistence",
                                     **categorical_scores(yy, pers[sel] == 1)})
                    for reading in ("prev", "worst"):
                        rows_out.append({**base, "forecast": f"{key}_{reading}",
                                         **categorical_scores(yy, extra[f"{key}_{reading}"][sel] == 1)})
                    if key == "trend" and part == "test":
                        dd = _day_codes(idx[sel])
                        b2 = bootstrap_categorical(
                            {"lgbm": (pred["lgbm"].to_numpy()[sel] >= thr["lgbm"]).astype(int),
                             "trend_prev": extra["trend_prev"][sel].astype(int),
                             "trend_worst": extra["trend_worst"][sel].astype(int)},
                            yy.astype(int), dd)
                        for ref in ("trend_prev", "trend_worst"):
                            for metric in ("CSI", "HSS"):
                                diff = b2["lgbm"][metric] - b2[ref][metric]
                                lo, hi = ci(diff)
                                paired_rows.append({"target": target, "h": h, "model": "lgbm",
                                                    "vs": ref, "metric": metric,
                                                    "diff_mean": float(np.nanmean(diff)),
                                                    "lo": lo, "hi": hi,
                                                    "significant": bool(lo > 0 or hi < 0)})

            # --------------------------------------------------------- per season (test)
            seasons = fog_season(idx)
            for s in np.unique(seasons[m]):
                sel = m & (seasons == s)
                if y_all[sel].sum() == 0:
                    continue
                row = {"target": target, "h": h, "season": f"{s}/{str(s + 1)[2:]}",
                       "events": int(y_all[sel].sum())}
                for name in [c for c in TAB + DEEP if c in pred]:
                    row[f"{name}_CSI"] = categorical_scores(
                        y_all[sel], pred[name].to_numpy()[sel] >= thr[name])["CSI"]
                    row[f"{name}_PRAUC"] = average_precision_score(y_all[sel], pred[name].to_numpy()[sel])
                row["persistence_CSI"] = categorical_scores(y_all[sel], pers[sel] == 1)["CSI"]
                season_rows.append(row)

    # ------------------------------------------------------------------ RVR multi-class
    for h in HORIZONS:
        if not all((PRED_DIR / f"pred_{t}_{h}h.parquet").exists() for t in ("rvr550", "rvr350")):
            continue
        p550, t550 = load_task("rvr550", h)
        p350, t350 = load_task("rvr350", h)
        idx = p550.index.intersection(p350.index)
        p550, p350 = p550.loc[idx], p350.loc[idx]
        y_cls = targ[f"y_rvr_{h}h"].reindex(idx).to_numpy().astype(int)
        split = p550["split"].to_numpy()
        tr = split == "train"
        vt = idx + pd.Timedelta(hours=h)
        key = vt.month * 100 + vt.hour
        clim_cls = np.column_stack([
            pd.Series((y_cls[tr] == k).astype(float)).groupby(key[tr]).mean().reindex(key).fillna(
                (y_cls[tr] == k).mean()).to_numpy() for k in range(3)])
        r = feats["rvr_eff_m"].reindex(idx).to_numpy()
        pers_cls = np.where(r < RVR_CAT_II_M, 2, np.where(r < RVR_CAT_I_M, 1, 0))
        for part in ("val", "test"):
            sel = split == part
            for name in [c for c in TAB + DEEP if c in p550 and c in p350]:
                probs = rvr_class_probs(p550[name].to_numpy()[sel], p350[name].to_numpy()[sel])
                yhat = np.where(p350[name].to_numpy()[sel] >= t350[name], 2,
                                np.where(p550[name].to_numpy()[sel] >= t550[name], 1, 0))
                ms = multiclass_scores(y_cls[sel], probs, yhat, clim_cls[sel])
                rvr_rows.append({"h": h, "split": part, "model": name,
                                 **{k: v for k, v in ms.items() if k not in ("ge1", "ge2")},
                                 "CSI_ge1": ms["ge1"]["CSI"], "CSI_ge2": ms["ge2"]["CSI"],
                                 "POD_ge2": ms["ge2"]["POD"], "FAR_ge2": ms["ge2"]["FAR"]})
            onehot = np.eye(3)[pers_cls[sel]]
            ms = multiclass_scores(y_cls[sel], onehot, pers_cls[sel], clim_cls[sel])
            rvr_rows.append({"h": h, "split": part, "model": "persistence",
                             **{k: v for k, v in ms.items() if k not in ("ge1", "ge2")},
                             "CSI_ge1": ms["ge1"]["CSI"], "CSI_ge2": ms["ge2"]["CSI"],
                             "POD_ge2": ms["ge2"]["POD"], "FAR_ge2": ms["ge2"]["FAR"]})

    od = onset_dissipation(feats, {h: pred_fog_by_h[h] for h in HORIZONS if h in pred_fog_by_h},
                           thr_fog_by_h)
    for name, rows in (("scores_all", all_rows), ("bootstrap_test", boot_rows),
                       ("paired_tests", paired_rows), ("trend_comparison", trend_rows),
                       ("taf_comparison", taf_rows), ("per_season", season_rows),
                       ("rvr_multiclass", rvr_rows), ("onset_dissipation", od),
                       ("leadtime_curve", lead_rows)):
        pd.DataFrame(rows).to_csv(TABLES / f"{name}.csv", index=False)
    sc = pd.DataFrame(all_rows)
    best = sc[(sc.split == "test") & (sc.season == "all") & (sc.kind == "ML")]
    summary["best_by_task"] = (best.sort_values("PR_AUC", ascending=False)
                               .groupby(["target", "h"]).head(1)
                               [["target", "h", "model", "PR_AUC", "BSS", "CSI", "HSS"]]
                               .to_dict(orient="records"))
    summary["n_taf"] = len(taf_arch.tafs)
    (RESULTS / "metrics.json").write_text(json.dumps(summary, indent=2, default=float))
    cols = ["target", "h", "model", "PR_AUC", "ROC_AUC", "Brier", "BSS", "POD", "FAR", "CSI", "HSS"]
    view = sc[(sc.split == "test") & (sc.season == "all")][cols]
    with pd.option_context("display.width", 200):
        print(view.round(3).to_string(index=False))
        print(pd.DataFrame(od).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
