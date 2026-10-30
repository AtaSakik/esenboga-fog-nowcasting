import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga import inference  # noqa: E402

REPORTS = pd.DataFrame({
    "obs_time": pd.to_datetime(["2026-10-30 10:50", "2026-10-30 10:20", "2026-10-30 10:50"], utc=True),
    "raw": ["METAR LTAC 301050Z", "METAR LTAC 301020Z", "METAR LTAC 301050Z"],
    "source": "IEM", "type_hint": None,
})


def _fail(exc):
    def fetch(hours):
        raise exc
    return fetch


def test_awc_is_retried_before_falling_back_to_iem(monkeypatch, capsys):
    calls = []

    def awc(hours):
        calls.append(hours)
        raise TimeoutError("timed out")

    monkeypatch.setattr(inference, "fetch_awc", awc)
    monkeypatch.setattr(inference, "fetch_iem", lambda hours: REPORTS)
    monkeypatch.setattr(inference.time, "sleep", lambda s: None)
    df, source = inference.fetch_reports()
    assert source == "IEM" and len(calls) == 2
    assert list(df["obs_time"]) == sorted(set(REPORTS["obs_time"]))     # deduplicated, oldest first
    assert capsys.readouterr().err.count("METAR source failed: aviationweather.gov") == 2


def test_every_source_failing_raises(monkeypatch):
    monkeypatch.setattr(inference, "fetch_awc", lambda hours: pd.DataFrame())
    monkeypatch.setattr(inference, "fetch_iem", _fail(OSError("down")))
    monkeypatch.setattr(inference.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="no METAR source reachable"):
        inference.fetch_reports()
