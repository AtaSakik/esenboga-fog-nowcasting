import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.baselines import expert_rule  # noqa: E402
from esenboga.benchmark import select_ensemble, weighted_mean  # noqa: E402
from esenboga.metrics import relative_value, sedi  # noqa: E402

Y = np.array([1, 0, 0, 1, 0, 0, 0, 0, 1, 0])


def test_relative_value_bounds():
    alpha = np.array([0.05, 0.2, 0.5])
    assert np.allclose(relative_value(Y, Y == 1, alpha), 1.0)            # perfect forecast
    never = relative_value(Y, np.zeros_like(Y, bool), alpha)
    always = relative_value(Y, np.ones_like(Y, bool), alpha)
    s = Y.mean()                                                          # 0.3
    assert np.allclose(never[alpha >= s], 0.0) and np.allclose(always[alpha <= s], 0.0)


def test_sedi_limits():
    assert np.isnan(sedi(1.0, 0.1)) and np.isnan(sedi(0.5, 0.0))
    assert abs(sedi(0.5, 0.5)) < 1e-12                                    # random forecast
    assert sedi(0.9, 0.01) > sedi(0.6, 0.01) > 0                          # more hits, more skill


def test_ensemble_selects_the_informative_member():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    good = np.clip(y * 0.7 + rng.normal(0, 0.2, 500), 0, 1)
    noise = rng.random(500)
    weights = select_ensemble({"good": good, "noise": noise}, y)
    assert weights.get("good", 0) >= 1 and weights.get("good", 0) > weights.get("noise", 0)
    pred = pd.DataFrame({"a": [0.2, np.nan, 0.6], "b": [0.4, 0.8, np.nan]})
    assert np.allclose(weighted_mean(pred, {"a": 1, "b": 3}), [0.35, 0.8, 0.6])   # missing members skipped


def test_expert_rule():
    X = pd.DataFrame({"dpd_c": [0.3, 0.3, 2.0, np.nan], "wind_speed_kt": [2, 2, 2, 2],
                      "vt_is_night": [1, 0, 1, 1], "fog_now": [0, 0, 1, 0]})
    out = expert_rule(X, dpd_max=0.5, wind_max=3, night_only=True, with_persistence=True)
    assert out[0] == 1 and out[1] == 0 and out[2] == 1 and np.isnan(out[3])
