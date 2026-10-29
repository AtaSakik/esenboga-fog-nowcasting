import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.config import INTERIM  # noqa: E402
from esenboga.features import (build_grid, make_features, make_targets,  # noqa: E402
                               solar_geometry)


def test_solar_geometry_ankara():
    t = pd.DatetimeIndex(["2024-06-21 10:00", "2024-12-21 10:00", "2024-12-21 22:00"])
    sg = solar_geometry(t)
    assert sg["solar_elev"].iloc[0] == pytest.approx(72.5, abs=1.5)   # summer local noon
    assert sg["solar_elev"].iloc[1] == pytest.approx(26.4, abs=1.5)   # winter local noon
    assert sg["is_night"].iloc[2] == 1 and sg["is_night"].iloc[1] == 0
    assert 9.0 < 24 - sg["night_len_h"].iloc[1] < 10.0                # ~9.5 h day at solstice


@pytest.fixture(scope="module")
def reports():
    p = INTERIM / "reports_decoded.parquet"
    if not p.exists():
        pytest.skip("run scripts/01_prepare_data.py first")
    d = pd.read_parquet(p)
    return d[(d.obs_time >= "2023-12-01") & (d.obs_time < "2024-01-15")].reset_index(drop=True)


def test_no_lookahead_leakage(reports):
    """Features at t must be identical when all reports after t are removed."""
    grid_full = build_grid(reports, start="2023-12-01")
    feat_full = make_features(grid_full)
    rng = np.random.default_rng(0)
    for t in rng.choice(feat_full.index[200:], size=12, replace=False):
        cut = reports[reports.obs_time <= t]
        feat_cut = make_features(build_grid(cut, start="2023-12-01", end=t))
        a, b = feat_full.loc[t], feat_cut.loc[t]
        pd.testing.assert_series_equal(a, b, check_names=False)


def test_targets_come_from_the_future(reports):
    grid = build_grid(reports, start="2023-12-01")
    targ = make_targets(grid, [1, 3])
    fog = (grid["vis_m"] < 1000).astype(float).where(grid["vis_m"].notna())
    pd.testing.assert_series_equal(targ["y_fog_1h"].iloc[:-2], fog.iloc[2:].set_axis(
        fog.index[:-2]), check_names=False)
    # an observation can only fill the slot (t-29 min, t]: target never re-uses the obs at t
    assert (grid["obs_age_min"].dropna() < 30).all()
