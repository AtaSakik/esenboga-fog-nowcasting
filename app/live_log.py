"""Live prediction log (SQLite) with automatic verification against later METARs.

Every nowcast cycle stores the calibrated probabilities; once the valid time has passed the
observed outcome is filled in from the decoded reports, which yields a genuinely real-time
verification record (mode='live'). ``backfill`` replays the recent past with the same code
(mode='replay') so that the dashboard is populated immediately after the first start.

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
from esenboga.features import rvr_effective  # noqa: E402

DB = LOGS / "live_predictions.sqlite"
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
        lookup = {t.isoformat(): (v, r) for t, v, r in
                  zip(state.index, state["vis_m"], state["rvr_eff"])}
        n = 0
        with self._con() as c:
            pending = c.execute("SELECT issue_time, horizon, target, valid_time FROM predictions"
                                " WHERE observed IS NULL").fetchall()
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

    def frame(self, hours: float | None = None) -> pd.DataFrame:
        with self._con() as c:
            df = pd.read_sql_query("SELECT * FROM predictions", c)
        if len(df):
            for col in ("issue_time", "valid_time"):
                df[col] = pd.to_datetime(df[col], utc=True)
            if hours:
                df = df[df["issue_time"] >= df["issue_time"].max() - pd.Timedelta(hours=hours)]
        return df

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


def cycle(nc, log: LiveLog) -> dict:
    """One operational cycle: fetch, predict, log, verify."""
    from esenboga.inference import fetch_reports

    reports, source = fetch_reports()
    grid, base, _ = nc.features_from_reports(reports)
    t = base.index[grid["vis_m"].notna().to_numpy()][-1]
    pred = nc.predict_at(base, t, explain=False)
    added = log.record(t, pred, mode="live")
    verified = log.verify(grid)
    return {"issue_time": t.isoformat(), "source": source, "added": added, "verified": verified}


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
    args = ap.parse_args()
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
