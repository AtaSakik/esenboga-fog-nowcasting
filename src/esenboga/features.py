"""Grid construction, feature engineering and target definition.

The same functions are used offline (20-year archive) and online (web application): the app
feeds the last ~30 h of decoded METARs through :func:`build_grid` and :func:`make_features`
and reads the last row. Every feature at grid time ``t`` depends only on reports issued at or
before ``t`` (verified by ``tests/test_leakage.py``).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (GRID_FREQ, GRID_OFFSET, LAT, LON, RVR_CAT_I_M, RVR_CAT_II_M, VIS_FOG_M)

# Columns of the decoded report table that are carried onto the grid.
STATE_COLS = [
    "vis_m", "vis_min_m", "rvr_min_m", "rvr_n", "temp_c", "dewpt_c", "dpd_c", "rh_pct",
    "wind_dir", "wind_speed_kt", "wind_gust_kt", "wind_vrb", "wind_var_range", "qnh_hpa",
    "ceiling_ft", "lowest_cloud_ft", "max_cover_octas", "vv_ft", "n_cloud_layers", "cavok",
    "wx_fg", "wx_shallow_fg", "wx_vcfg", "wx_fzfg", "wx_br", "wx_hz", "wx_dz", "wx_ra",
    "wx_sn", "wx_precip", "wx_ts", "recent_precip",
]
CEILING_CAP_FT = 10000.0     # "no ceiling" / very high ceilings are capped here
VIS_CAP_M = 10000.0


# ============================================================================ astronomy
def solar_geometry(times: pd.DatetimeIndex, lat: float = LAT, lon: float = LON) -> pd.DataFrame:
    """Solar elevation and sunrise/sunset times (NOAA general solar position equations)."""
    t = pd.DatetimeIndex(times)
    if t.tz is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    doy = t.day_of_year.to_numpy()
    hour = (t.hour + t.minute / 60.0).to_numpy()
    g = 2 * np.pi / 365.0 * (doy - 1 + (hour - 12) / 24.0)
    eqtime = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                       - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    phi = np.radians(lat)
    tst = hour * 60.0 + eqtime + 4.0 * lon                 # true solar time (min)
    ha = np.radians(tst / 4.0 - 180.0)
    cos_zen = np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(ha)
    elev = 90.0 - np.degrees(np.arccos(np.clip(cos_zen, -1, 1)))
    # sunrise / sunset (UTC hours) for the current day, zenith 90.833 deg
    cos_ha0 = (np.cos(np.radians(90.833)) / (np.cos(phi) * np.cos(decl))
               - np.tan(phi) * np.tan(decl))
    ha0 = np.degrees(np.arccos(np.clip(cos_ha0, -1, 1)))
    sunrise = (720.0 - 4.0 * (lon + ha0) - eqtime) / 60.0
    sunset = (720.0 - 4.0 * (lon - ha0) - eqtime) / 60.0
    night = (hour < sunrise) | (hour >= sunset)
    since_sunset = np.where(hour >= sunset, hour - sunset,
                            np.where(hour < sunrise, hour + 24.0 - sunset, 0.0))
    to_sunrise = np.where(hour < sunrise, sunrise - hour,
                          np.where(hour >= sunset, sunrise + 24.0 - hour, 0.0))
    since_sunrise = np.where(night, 0.0, hour - sunrise)
    return pd.DataFrame({
        "solar_elev": elev, "is_night": night.astype(float), "h_since_sunset": since_sunset,
        "h_to_sunrise": to_sunrise, "h_since_sunrise": since_sunrise,
        "night_len_h": 24.0 - (sunset - sunrise),
    }, index=times)


# ============================================================================ grid
def build_grid(reports: pd.DataFrame, start=None, end=None, max_age_min: int = 30) -> pd.DataFrame:
    """Regular 30-min grid (HH:20/HH:50 UTC) holding the latest report issued in
    ``(t - max_age_min, t]``. Missing observations stay NaN (no interpolation)."""
    rep = reports.sort_values("obs_time").drop_duplicates("obs_time", keep="last")
    rep = rep.set_index("obs_time")
    def _ts(x):
        x = pd.Timestamp(x)
        if rep.index.tz is not None and x.tz is None:
            x = x.tz_localize(rep.index.tz)
        return x

    t0 = _ts(start if start is not None else rep.index.min()).floor("h")
    t1 = _ts(end if end is not None else rep.index.max())
    grid = pd.date_range(t0 + pd.Timedelta(GRID_OFFSET), t1, freq=GRID_FREQ, tz=rep.index.tz)
    cols = [c for c in STATE_COLS if c in rep.columns]
    src = rep[cols].copy()
    src["obs_time"] = rep.index
    st = pd.merge_asof(pd.DataFrame(index=grid).rename_axis("time").reset_index(),
                       src.reset_index(drop=True).sort_values("obs_time"),
                       left_on="time", right_on="obs_time", direction="backward",
                       tolerance=pd.Timedelta(minutes=max_age_min - 1))
    st = st.set_index("time")
    st["obs_age_min"] = (st.index - st["obs_time"]).dt.total_seconds() / 60.0
    return st.drop(columns=["obs_time"])


# ============================================================================ targets
def rvr_effective(vis_m: pd.Series, rvr_min_m: pd.Series) -> pd.Series:
    """Operational RVR used for the ILS-category label.

    The minimum reported RVR over all runways is used. When no RVR group is present, RVR is not
    required (visibility >= 1500 m) and the category is CAT I+; if visibility < 1500 m but RVR
    is missing, the prevailing visibility is used as a conservative proxy (RVR >= MOR because
    runway lights extend the visual range)."""
    eff = rvr_min_m.copy()
    no_rvr = eff.isna()
    eff[no_rvr & (vis_m >= 1500)] = 2000.0
    eff[no_rvr & (vis_m < 1500)] = vis_m[no_rvr & (vis_m < 1500)]
    return eff


def rvr_class(rvr_eff: pd.Series) -> pd.Series:
    cls = pd.Series(np.where(rvr_eff < RVR_CAT_II_M, 2,
                             np.where(rvr_eff < RVR_CAT_I_M, 1, 0)).astype(float),
                    index=rvr_eff.index)
    cls[rvr_eff.isna()] = np.nan
    return cls


def make_targets(grid: pd.DataFrame, horizons) -> pd.DataFrame:
    """Targets at valid time t+h for every grid time t (NaN when the obs at t+h is missing)."""
    out = {}
    vis = grid["vis_m"]
    rvr_e = rvr_effective(vis, grid["rvr_min_m"])
    fog = (vis < VIS_FOG_M).astype(float).where(vis.notna())
    cls = rvr_class(rvr_e)
    steps_per_h = 2
    for h in horizons:
        k = h * steps_per_h
        out[f"y_fog_{h}h"] = fog.shift(-k)
        out[f"y_rvr_{h}h"] = cls.shift(-k)
        out[f"vis_{h}h"] = vis.shift(-k)
    out["y_fog_0h"] = fog
    out["y_rvr_0h"] = cls
    out["rvr_eff_0h"] = rvr_e
    return pd.DataFrame(out, index=grid.index)


# ============================================================================ features
def _lag(s: pd.Series, hours: float) -> pd.Series:
    return s.shift(int(round(hours * 2)))


def _roll(s: pd.Series, hours: float, fn: str) -> pd.Series:
    w = int(round(hours * 2))
    r = s.rolling(w, min_periods=max(1, w // 2))
    return getattr(r, fn)()


def make_features(grid: pd.DataFrame) -> pd.DataFrame:
    """Feature matrix at every grid time (uses data at or before each time only)."""
    g = grid
    f = pd.DataFrame(index=g.index)
    vis = g["vis_m"].clip(upper=VIS_CAP_M)
    logvis = np.log10(vis.clip(lower=25))
    f["vis_m"] = vis
    f["log_vis"] = logvis
    f["vis_min_m"] = g["vis_min_m"].fillna(vis).clip(upper=VIS_CAP_M)
    f["rvr_eff_m"] = rvr_effective(vis, g["rvr_min_m"])
    f["fog_now"] = (vis < VIS_FOG_M).astype(float).where(vis.notna())
    f["temp_c"] = g["temp_c"]
    f["dewpt_c"] = g["dewpt_c"]
    f["dpd_c"] = g["dpd_c"]
    f["rh_pct"] = g["rh_pct"]
    spd = g["wind_speed_kt"]
    rad = np.radians(g["wind_dir"])
    f["wind_speed_kt"] = spd
    f["wind_u"] = (-spd * np.sin(rad)).fillna(0.0).where(spd.notna())
    f["wind_v"] = (-spd * np.cos(rad)).fillna(0.0).where(spd.notna())
    f["calm"] = (spd <= 2).astype(float).where(spd.notna())
    f["gust_excess_kt"] = (g["wind_gust_kt"] - spd).fillna(0.0).where(spd.notna())
    f["qnh_hpa"] = g["qnh_hpa"]
    ceil = g["ceiling_ft"].replace(np.inf, CEILING_CAP_FT).clip(upper=CEILING_CAP_FT)
    low = g["lowest_cloud_ft"].replace(np.inf, CEILING_CAP_FT).clip(upper=CEILING_CAP_FT)
    f["log_ceiling_ft"] = np.log10(ceil.clip(lower=50))
    f["log_lowest_cloud_ft"] = np.log10(low.clip(lower=50))
    f["max_cover_octas"] = g["max_cover_octas"]
    f["low_cloud"] = (low <= 1000).astype(float).where(low.notna())
    f["vv_reported"] = g["vv_ft"].notna().astype(float).where(vis.notna())
    for c in ("cavok", "wx_fg", "wx_shallow_fg", "wx_vcfg", "wx_fzfg", "wx_br", "wx_hz",
              "wx_dz", "wx_ra", "wx_sn", "wx_precip", "recent_precip"):
        f[c] = g[c].astype(float)

    # ---------------------------------------------------------------- tendencies
    for h in (1, 3, 6):
        f[f"dT_{h}h"] = g["temp_c"] - _lag(g["temp_c"], h)
        f[f"dTd_{h}h"] = g["dewpt_c"] - _lag(g["dewpt_c"], h)
        f[f"ddpd_{h}h"] = g["dpd_c"] - _lag(g["dpd_c"], h)
        f[f"dlogvis_{h}h"] = logvis - _lag(logvis, h)
    for h in (1, 3):
        f[f"drh_{h}h"] = g["rh_pct"] - _lag(g["rh_pct"], h)
        f[f"dwind_{h}h"] = spd - _lag(spd, h)
    f["dqnh_3h"] = g["qnh_hpa"] - _lag(g["qnh_hpa"], 3)
    f["dqnh_12h"] = g["qnh_hpa"] - _lag(g["qnh_hpa"], 12)
    f["dlogceil_3h"] = f["log_ceiling_ft"] - _lag(f["log_ceiling_ft"], 3)

    # ---------------------------------------------------------------- history / memory
    fog_state = f["fog_now"]
    f["T_minus_max12h"] = g["temp_c"] - _roll(g["temp_c"], 12, "max")   # nocturnal cooling
    f["dpd_min_6h"] = _roll(g["dpd_c"], 6, "min")
    f["rh_max_6h"] = _roll(g["rh_pct"], 6, "max")
    f["wind_mean_3h"] = _roll(spd, 3, "mean")
    f["vis_min_3h"] = _roll(vis, 3, "min")
    f["vis_min_6h"] = _roll(vis, 6, "min")
    f["fog_frac_6h"] = _roll(fog_state, 6, "mean")
    f["fog_frac_24h"] = _roll(fog_state, 24, "mean")
    f["br_frac_6h"] = _roll(g["wx_br"].astype(float), 6, "mean")
    f["precip_frac_12h"] = _roll(g["wx_precip"].astype(float), 12, "mean")
    f["snow_frac_72h"] = _roll(g["wx_sn"].astype(float), 72, "mean")
    # hours since visibility was last below 1000 m (capped at 96 h)
    last_fog_time = pd.Series(np.where(fog_state == 1, np.arange(len(g)), np.nan),
                              index=g.index).ffill()
    f["h_since_fog"] = ((np.arange(len(g)) - last_fog_time) / 2.0).clip(upper=96).fillna(96)
    f["obs_age_min"] = g["obs_age_min"]

    # ---------------------------------------------------------------- calendar / sun
    t = g.index.tz_convert("UTC") if g.index.tz is not None else g.index
    hour = t.hour + t.minute / 60.0
    doy = t.day_of_year
    f["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    f["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    f["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    f["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    sg = solar_geometry(g.index)
    for c in ("solar_elev", "is_night", "h_since_sunset", "h_to_sunrise", "night_len_h"):
        f[c] = sg[c].to_numpy()
    return f


def valid_time_features(index: pd.DatetimeIndex, h: int) -> pd.DataFrame:
    """Deterministic (known-in-advance) astronomical features at the valid time t+h."""
    vt = index + pd.Timedelta(hours=h)
    sg = solar_geometry(vt)
    return pd.DataFrame({
        "vt_solar_elev": sg["solar_elev"].to_numpy(),
        "vt_is_night": sg["is_night"].to_numpy(),
        "vt_h_to_sunrise": sg["h_to_sunrise"].to_numpy(),
        "vt_h_since_sunrise": sg["h_since_sunrise"].to_numpy(),
    }, index=index)


def feature_matrix(grid: pd.DataFrame, h: int, base: pd.DataFrame | None = None) -> pd.DataFrame:
    base = make_features(grid) if base is None else base
    return pd.concat([base, valid_time_features(base.index, h)], axis=1)
