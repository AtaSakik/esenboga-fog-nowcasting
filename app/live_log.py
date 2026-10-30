"""Live prediction log (SQLite) with automatic verification against later METARs.

Every nowcast cycle stores the calibrated probabilities; once the valid time has passed the
observed outcome is filled in from the decoded reports, which yields a genuinely real-time
verification record (mode='live'). ``backfill`` replays the recent past with the same code
(mode='replay') so that the dashboard is populated immediately after the first start, and
``catch_up`` computes, in the next cycle, the forecasts for issue times a scheduler skipped
(mode='catchup', kept apart from the real-time record).

CLI:  python app/live_log.py --once | --loop [--every 600] | --summary
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from esenboga.config import LOGS, RVR_CAT_I_M, RVR_CAT_II_M, VIS_FOG_M  # noqa: E402
from esenboga.features import MEMORY_H, rvr_effective  # noqa: E402

DB = LOGS / "live_predictions.sqlite"
# A skipped issue time is caught up only when the fetched reports reach at least this far back
# before it, so its features use the same history as in real time (MEMORY_H + 4-h margin); only
# reports corrected after the fact (COR) can differ from what the skipped run would have seen.
# With the 7-day fetch (inference.HISTORY_H) this covers about the last 68 h.
CATCHUP_MIN_HISTORY_H = MEMORY_H + 4
SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    issue_time TEXT NOT NULL, horizon INTEGER NOT NULL, target TEXT NOT NULL,
    prob REAL NOT NULL, threshold REAL, valid_time TEXT NOT NULL, mode TEXT NOT NULL,
    created_at TEXT NOT NULL, observed INTEGER, obs_vis REAL, obs_rvr REAL,
    PRIMARY KEY (issue_time, horizon, target));
"""


class LiveLog:
    def __init__(self, path: Path = DB):
        self.path = path
        with self._con() as c:
            c.executescript(SCHEMA)

    def _con(self):
        return sqlite3.connect(self.path)

    def record(self, issue_time: pd.Timestamp, pred: dict, mode: str = "live") -> int:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = []
        for h, v in pred["fog"].items():
            rows.append((issue_time.isoformat(), int(h), "fog", v["p"], v["threshold"],
                         (issue_time + pd.Timedelta(hours=int(h))).isoformat(), mode, now))
        for h, v in pred.get("rvr", {}).items():
            for tgt, key in (("rvr550", "p_lt550"), ("rvr350", "p_lt350")):
                rows.append((issue_time.isoformat(), int(h), tgt, v[key], None,
                             (issue_time + pd.Timedelta(hours=int(h))).isoformat(), mode, now))
        with self._con() as c:
            c.executemany("INSERT OR IGNORE INTO predictions (issue_time, horizon, target, prob,"
                          " threshold, valid_time, mode, created_at) VALUES (?,?,?,?,?,?,?,?)",
                          rows)
            return c.total_changes

    def verify(self, grid: pd.DataFrame) -> int:
        """Fill observed outcomes for predictions whose valid time is on the grid."""
        state = grid[["vis_m", "rvr_min_m"]].dropna(subset=["vis_m"])
        state = state.assign(rvr_eff=rvr_effective(state["vis_m"], state["rvr_min_m"]))
        if state.empty:
            return 0
        lookup = {t.isoformat(): (v, r) for t, v, r in
                  zip(state.index, state["vis_m"], state["rvr_eff"])}
        n = 0
        with self._con() as c:
            # only valid times inside the fetched window can be verified (ISO strings sort in time)
            pending = c.execute("SELECT issue_time, horizon, target, valid_time FROM predictions"
                                " WHERE observed IS NULL AND valid_time BETWEEN ? AND ?",
                                (state.index[0].isoformat(), state.index[-1].isoformat())).fetchall()
            for it, h, tgt, vt in pending:
                if vt not in lookup:
                    continue
                vis, rvr = lookup[vt]
                if tgt == "fog":
                    obs = int(vis < VIS_FOG_M)
                elif tgt == "rvr550":
                    obs = int(rvr < RVR_CAT_I_M)
                else:
                    obs = int(rvr < RVR_CAT_II_M)
                c.execute("UPDATE predictions SET observed=?, obs_vis=?, obs_rvr=? WHERE "
                          "issue_time=? AND horizon=? AND target=?",
                          (obs, float(vis), float(rvr), it, h, tgt))
                n += 1
        return n

    def issue_times(self) -> dict[str, str]:
        """{issue time (ISO): mode} of every logged forecast."""
        with self._con() as c:
            return dict(c.execute("SELECT DISTINCT issue_time, mode FROM predictions").fetchall())

    def frame(self, hours: float | None = None) -> pd.DataFrame:
        with self._con() as c:
            df = pd.read_sql_query("SELECT * FROM predictions", c)
        if len(df):
            for col in ("issue_time", "valid_time"):
                df[col] = pd.to_datetime(df[col], utc=True)
            if hours is not None:
                df = df[df["issue_time"] >= df["issue_time"].max() - pd.Timedelta(hours=hours)]
        return df

    def forecasts_json(self, hours: float = 72.0, horizon: int = 3) -> list[dict]:
        """Fog forecasts of one lead time with their outcomes (the dashboard's api/log)."""
        df = self.frame(hours)
        if df.empty:
            return []
        df = df[(df["target"] == "fog") & (df["horizon"] == horizon)].sort_values("valid_time")
        return [{"valid_time": v.isoformat(), "issue_time": i.isoformat(), "p": p, "thr": th,
                 "observed": None if pd.isna(o) else int(o), "obs_vis": None if pd.isna(ov) else ov,
                 "mode": m}
                for v, i, p, th, o, ov, m in zip(df["valid_time"], df["issue_time"], df["prob"],
                                                 df["threshold"], df["observed"], df["obs_vis"],
                                                 df["mode"])]

    def summary(self) -> list[dict]:
        df = self.frame()
        out = []
        if not len(df):
            return out
        df = df[df["observed"].notna() & (df["target"] == "fog")]
        for (mode, h), g in df.groupby(["mode", "horizon"]):
            y = g["observed"].to_numpy().astype(int)
            yhat = (g["prob"] >= g["threshold"]).to_numpy()
            a = int((yhat & (y == 1)).sum())
            b = int((yhat & (y == 0)).sum())
            cc = int((~yhat & (y == 1)).sum())
            out.append({"mode": mode, "horizon": int(h), "n": int(len(g)), "events": int(y.sum()),
                        "hits": a, "false_alarms": b, "misses": cc,
                        "POD": a / (a + cc) if a + cc else None,
                        "FAR": b / (a + b) if a + b else None,
                        "CSI": a / (a + b + cc) if a + b + cc else None,
                        "Brier": float(np.mean((g["prob"] - y) ** 2)),
                        "first": g["issue_time"].min().isoformat(),
                        "last": g["issue_time"].max().isoformat()})
        return out


def missed_issue_times(grid: pd.DataFrame, known: dict[str, str], latest: pd.Timestamp,
                       min_history_h: float = CATCHUP_MIN_HISTORY_H) -> list[pd.Timestamp]:
    """Issue times the live cycle skipped: grid times with an observation, after the first live
    forecast and before ``latest``, that have no forecast yet and are preceded by at least
    ``min_history_h`` of the fetched reports."""
    live = [pd.Timestamp(t) for t, mode in known.items() if mode == "live"]
    obs = grid.index[grid["vis_m"].notna().to_numpy()]
    if not live or not len(obs):
        return []
    start = max(min(live), obs[0] + pd.Timedelta(hours=min_history_h))
    return [t for t in obs if start <= t < latest and t.isoformat() not in known]


def catch_up(nc, log: LiveLog, grid: pd.DataFrame, base: pd.DataFrame, latest: pd.Timestamp) -> int:
    """Forecast the skipped issue times from the reports observed up to each of them (as fetched
    now, so later corrections are included)."""
    missed = missed_issue_times(grid, log.issue_times(), latest)
    for t in missed:
        log.record(t, nc.predict_at(base, t, explain=False), mode="catchup")
    return len(missed)


def run_cycle(nc, log: LiveLog) -> tuple[dict, dict]:
    """One operational cycle shared by the FastAPI server, the static publisher and the CLI:
    fetch, forecast (with explanations), log, catch up skipped issue times and verify.
    Returns (nowcast, counts)."""
    from esenboga.inference import fetch_reports, run_nowcast

    reports, source = fetch_reports()
    grid, base, clean = nc.features_from_reports(reports)
    res = run_nowcast(nc, source=source, prepared=(grid, base, clean))
    latest = pd.Timestamp(res["issue_time"])
    added = log.record(latest, {"fog": res["fog"], "rvr": res["rvr"]}, mode="live")
    caught_up = catch_up(nc, log, grid, base, latest)
    verified = log.verify(grid)
    return res, {"added": added, "caught_up": caught_up, "verified": verified}


def cycle(nc, log: LiveLog) -> dict:
    """CLI cycle: the shared cycle, reported as one line of JSON."""
    res, counts = run_cycle(nc, log)
    return {"issue_time": res["issue_time"], "source": res["source"], "alert": res["alert"], **counts}


def backfill(nc, log: LiveLog, hours: int = 72) -> int:
    """Replay the last ``hours`` with the operational code path (mode='replay')."""
    from esenboga.inference import fetch_reports

    reports, _ = fetch_reports(hours=hours + 100)
    grid, base, _ = nc.features_from_reports(reports)
    times = base.index[grid["vis_m"].notna().to_numpy()]
    times = times[times >= times[-1] - pd.Timedelta(hours=hours)]
    n = 0
    for t in times[:-1]:
        n += log.record(t, nc.predict_at(base, t, explain=False), mode="replay") > 0
    log.verify(grid)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--every", type=int, default=600)
    ap.add_argument("--backfill", type=int, default=0, help="replay the last N hours")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--logfile", default=None,
                    help="append each cycle's outcome to this file (for scheduled, windowless runs)")
    args = ap.parse_args()
    if args.logfile:
        # pythonw.exe has no console: send the cycle reports to a file instead
        sys.stdout = sys.stderr = open(args.logfile, "a", encoding="utf-8", buffering=1)
        print(f"--- {datetime.now(timezone.utc).isoformat(timespec='seconds')} start", flush=True)
    log = LiveLog()
    if args.summary:
        print(json.dumps(log.summary(), indent=2))
        return
    from esenboga.inference import Nowcaster

    nc = Nowcaster()
    if args.backfill:
        print("replayed", backfill(nc, log, args.backfill), "issue times")
    if args.once or args.loop:
        while True:
            try:
                print(json.dumps(cycle(nc, log)), flush=True)
            except Exception as exc:          # keep the logger alive across network errors
                print(f"cycle failed: {exc!r}", flush=True)
            if not args.loop:
                break
            time.sleep(args.every)


if __name__ == "__main__":
    main()
