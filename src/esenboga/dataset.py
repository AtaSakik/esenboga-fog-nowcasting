"""Assemble the quality-controlled LTAC report table from the raw archives.

Sources (priority order for the same observation time):
  1. IEM ASOS archive, original METAR/SPECI text (records rebuilt from NCEI ISD/DS3505 and
     tagged ``IEM_DS3505`` are *not* original reports – no RVR, no TREND, visibility in
     statute-mile steps – and are discarded);
  2. Ogimet ``getmetar`` archive (original text, used to fill IEM gaps 2005-2012).
"""
from __future__ import annotations

import glob
import gzip
import re

import numpy as np
import pandas as pd

from .config import RAW_METAR, STATION
from .metar import flatten, parse_metar

QC_LIMITS = {
    "temp_c": (-35.0, 45.0),
    "dewpt_c": (-45.0, 35.0),
    "qnh_hpa": (960.0, 1060.0),
    "wind_speed_kt": (0.0, 100.0),
    "vis_m": (0.0, 10000.0),
    "rvr_min_m": (0.0, 2500.0),
}
SPIKE_THRESHOLDS = {"temp_c": 8.0, "dewpt_c": 8.0, "qnh_hpa": 6.0}


def load_iem(start_year: int) -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob(str(RAW_METAR / f"{STATION}_IEM_*.csv.gz"))):
        year = int(re.search(r"_(\d{4})\.csv\.gz$", f).group(1))
        if year < start_year:
            continue
        d = pd.read_csv(f)
        d = d[~d["metar"].str.contains("IEM_DS3505", na=False)]
        frames.append(pd.DataFrame({
            "obs_time": pd.to_datetime(d["valid"]).dt.tz_localize("UTC"),
            "raw": d["metar"].astype(str), "source": "IEM", "type_hint": None}))
    return pd.concat(frames, ignore_index=True)


def load_ogimet() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(RAW_METAR / f"{STATION}_OGIMET_*.csv.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split(",", 6)
                if len(parts) < 7 or " NIL" in parts[6]:
                    continue
                y, mo, d, hh, mi = map(int, parts[1:6])
                text = parts[6].strip()
                hint = "SPECI" if text.startswith("SPECI") else "METAR"
                rows.append((pd.Timestamp(y, mo, d, hh, mi, tz="UTC"), text, "OGIMET", hint))
    return pd.DataFrame(rows, columns=["obs_time", "raw", "source", "type_hint"])


def merge_sources(start_year: int = 2005) -> pd.DataFrame:
    iem = load_iem(start_year)
    ogm = load_ogimet()
    ogm = ogm[ogm["obs_time"].dt.year >= start_year]
    hints = ogm.set_index("obs_time")["type_hint"]
    hints = hints[~hints.index.duplicated()]
    both = pd.concat([iem, ogm], ignore_index=True)
    both["prio"] = both["source"].map({"IEM": 0, "OGIMET": 1})
    both = (both.sort_values(["obs_time", "prio"])
                .drop_duplicates("obs_time", keep="first")
                .drop(columns="prio").reset_index(drop=True))
    both["type_hint"] = both["obs_time"].map(hints)
    return both


def decode(reports: pd.DataFrame) -> pd.DataFrame:
    recs = []
    for t, raw in zip(reports["obs_time"], reports["raw"]):
        rec = parse_metar(raw, t.to_pydatetime())
        d = flatten(rec)
        d["obs_time"] = t                     # archive time stamp is authoritative
        recs.append(d)
    dec = pd.DataFrame.from_records(recs)
    dec["raw"] = reports["raw"].to_numpy()
    dec["source"] = reports["source"].to_numpy()
    minute = dec["obs_time"].dt.minute
    routine = minute.isin([20, 50])
    hint = reports["type_hint"].to_numpy()
    dec["report_type"] = np.where(hint == "SPECI", "SPECI",
                                  np.where(routine, "METAR", "SPECI"))
    return dec


def quality_control(dec: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Range checks, dew-point consistency and isolated-spike removal. Returns (clean, log)."""
    d = dec.sort_values("obs_time").reset_index(drop=True).copy()
    log = {"reports_in": len(d)}
    bad = d["nil"] | d["malformed"] | d["vis_m"].isna()
    log["dropped_nil_malformed_or_no_vis"] = int(bad.sum())
    d = d[~bad].reset_index(drop=True)
    for col, (lo, hi) in QC_LIMITS.items():
        out = (d[col] < lo) | (d[col] > hi)
        log[f"range_{col}"] = int(out.sum())
        d.loc[out, col] = np.nan
    dp_bad = d["dewpt_c"] > d["temp_c"] + 0.5
    log["dewpoint_above_temperature"] = int(dp_bad.sum())
    d.loc[dp_bad, "dewpt_c"] = np.nan
    gap_prev = d["obs_time"].diff().dt.total_seconds() / 3600
    gap_next = -d["obs_time"].diff(-1).dt.total_seconds() / 3600
    near = (gap_prev <= 2) & (gap_next <= 2)
    for col, thr in SPIKE_THRESHOLDS.items():
        a = d[col] - d[col].shift(1)
        b = d[col] - d[col].shift(-1)
        spike = near & (a.abs() > thr) & (b.abs() > thr) & (np.sign(a) == np.sign(b))
        log[f"spike_{col}"] = int(spike.sum())
        d.loc[spike, col] = np.nan
    # derived humidity variables must follow the cleaned temperature / dew point
    d["dpd_c"] = d["temp_c"] - d["dewpt_c"]
    a_, b_ = 17.625, 243.04
    d["rh_pct"] = (100 * np.exp(a_ * d["dewpt_c"] / (b_ + d["dewpt_c"])
                                - a_ * d["temp_c"] / (b_ + d["temp_c"]))).clip(upper=100)
    log["reports_out"] = len(d)
    return d, log
