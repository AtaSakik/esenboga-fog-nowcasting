"""Reference forecasts: persistence, METAR TREND and TAF, aligned to the analysis grid."""
from __future__ import annotations

import glob
import math

import numpy as np
import pandas as pd

from .config import INTERIM, RAW_TAF, STATION, VIS_FOG_M
from .metar import parse_metar, trend_vis_range
from .taf import TafArchive, read_ogimet_taf_file


def grid_raw_reports(index: pd.DatetimeIndex, max_age_min: int = 30) -> pd.Series:
    """Raw text of the report that defines the grid state at each time (same rule as
    :func:`esenboga.features.build_grid`)."""
    rep = pd.read_parquet(INTERIM / "reports_decoded.parquet", columns=["obs_time", "raw"])
    rep = rep.sort_values("obs_time").drop_duplicates("obs_time", keep="last")
    m = pd.merge_asof(pd.DataFrame({"time": index}), rep, left_on="time", right_on="obs_time",
                      direction="backward", tolerance=pd.Timedelta(minutes=max_age_min - 1))
    return pd.Series(m["raw"].to_numpy(), index=index)


def trend_forecasts(index: pd.DatetimeIndex, h: float) -> pd.DataFrame:
    """Visibility forecast of the METAR TREND issued at t for t+h (h <= 2 h)."""
    raws = grid_raw_reports(index)
    prev, worst = np.full(len(index), np.nan), np.full(len(index), np.nan)
    dt = pd.Timedelta(hours=h)
    for k, (t, raw) in enumerate(zip(index, raws)):
        if not isinstance(raw, str):
            continue
        rec = parse_metar(raw, t.to_pydatetime())
        if rec.obs_time is None:
            continue
        p, w = trend_vis_range(rec, (t + dt).to_pydatetime())
        prev[k], worst[k] = p, w
    return pd.DataFrame({"trend_vis_prev": prev, "trend_vis_worst": worst}, index=index)


def load_taf_archive() -> TafArchive:
    tafs = []
    for f in sorted(glob.glob(str(RAW_TAF / f"{STATION}_TAF_*.txt"))):
        from pathlib import Path
        tafs.extend(read_ogimet_taf_file(Path(f)))
    return TafArchive(tafs)


def taf_forecasts(index: pd.DatetimeIndex, h: float, archive: TafArchive | None = None) -> pd.DataFrame:
    """Visibility range forecast by the latest TAF issued at or before t for valid time t+h."""
    archive = archive or load_taf_archive()
    prev, worst = np.full(len(index), np.nan), np.full(len(index), np.nan)
    if archive.tafs:
        first, last = archive.tafs[0].issue_time, archive.tafs[-1].valid_to
        dt = pd.Timedelta(hours=h)
        for k, t in enumerate(index):
            vt = (t + dt).to_pydatetime()
            if vt < first or vt > last:
                continue
            p, w, _ = archive.lookup(vt, h)
            prev[k], worst[k] = p, w
    return pd.DataFrame({"taf_vis_prev": prev, "taf_vis_worst": worst}, index=index)


def vis_to_event(vis: pd.Series | np.ndarray, threshold: float = VIS_FOG_M) -> np.ndarray:
    v = np.asarray(vis, float)
    out = (v < threshold).astype(float)
    out[np.isnan(v)] = math.nan
    return out
