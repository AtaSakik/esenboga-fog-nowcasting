import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from live_log import LiveLog, missed_issue_times  # noqa: E402

PRED = {"fog": {1: {"p": 0.6, "threshold": 0.4}, 2: {"p": 0.1, "threshold": 0.4}}}


def _grid(n=10, start="2026-10-30 00:20"):
    idx = pd.date_range(start, periods=n, freq="30min", tz="UTC")
    return pd.DataFrame({"vis_m": 9999.0, "rvr_min_m": np.nan}, index=idx)


def test_catch_up_fills_only_skipped_operational_slots(tmp_path):
    grid = _grid()
    grid.iloc[4, 0] = np.nan                   # no report in this slot -> nothing to forecast
    idx = grid.index
    log = LiveLog(tmp_path / "log.sqlite")
    log.record(idx[0], PRED, mode="replay")    # before the system started
    log.record(idx[2], PRED, mode="live")      # first real-time forecast
    log.record(idx[6], PRED, mode="live")
    missed = missed_issue_times(grid, log.issue_times(), latest=idx[9], min_history_h=0)
    # idx[1] predates the first live forecast, idx[9] is the current issue time
    assert missed == [idx[3], idx[5], idx[7], idx[8]]


def test_catch_up_needs_the_full_feature_history(tmp_path):
    grid = _grid(n=60)                         # 30 h of half-hourly slots
    idx = grid.index
    log = LiveLog(tmp_path / "log.sqlite")
    assert missed_issue_times(grid, log.issue_times(), latest=idx[-1], min_history_h=0) == []  # no live yet
    log.record(idx[0], PRED, mode="live")
    missed = missed_issue_times(grid, log.issue_times(), latest=idx[-1], min_history_h=10)
    assert missed == list(idx[20:59])          # >= 10 h of reports before each, latest excluded
    # with the default (MEMORY_H + margin) a 30-h fetch is too short to recompute anything exactly
    assert missed_issue_times(grid, log.issue_times(), latest=idx[-1]) == []


def test_catch_up_rows_are_verified_and_summarised_apart(tmp_path):
    grid = _grid()
    idx = grid.index
    grid.loc[idx[5], "vis_m"] = 400.0          # fog at the 1-h valid time of idx[3]
    log = LiveLog(tmp_path / "log.sqlite")
    log.record(idx[2], PRED, mode="live")
    log.record(idx[3], PRED, mode="catchup")
    assert log.verify(grid) == 4
    rows = {(r["mode"], r["horizon"]): r for r in log.summary()}
    assert set(rows) == {("live", 1), ("live", 2), ("catchup", 1), ("catchup", 2)}
    assert rows[("catchup", 1)]["hits"] == 1 and rows[("live", 1)]["false_alarms"] == 1
    assert log.issue_times() == {idx[2].isoformat(): "live", idx[3].isoformat(): "catchup"}
