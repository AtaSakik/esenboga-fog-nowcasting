"""Serverless operational cycle (used by the GitHub Actions workflow).

Fetches the latest METARs, logs and verifies the calibrated forecasts in a SQLite database and
writes a static copy of the dashboard (HTML/CSS/JS + JSON "API" files) that GitHub Pages
serves. The dashboard code is the same as in the FastAPI application; only the data source
changes from live endpoints to the JSON files generated here.

Usage: python app/publish_static.py --db live/live_predictions.sqlite --out site
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from esenboga.inference import Nowcaster, fetch_reports, run_nowcast  # noqa: E402
from esenboga.labels import FEATURE_LABELS  # noqa: E402
from live_log import LiveLog  # noqa: E402


def log_json(log: LiveLog, hours: float = 72.0, horizon: int = 3) -> list[dict]:
    """Same structure as the /api/log endpoint of app/server.py."""
    df = log.frame(hours)
    if df.empty:
        return []
    df = df[(df["target"] == "fog") & (df["horizon"] == horizon)].sort_values("valid_time")
    return [{"valid_time": v.isoformat(), "issue_time": i.isoformat(), "p": p, "thr": th,
             "observed": None if o != o else int(o), "obs_vis": None if ov != ov else ov, "mode": m}
            for v, i, p, th, o, ov, m in zip(df["valid_time"], df["issue_time"], df["prob"],
                                             df["threshold"], df["observed"], df["obs_vis"],
                                             df["mode"])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    log = LiveLog(Path(args.db))
    nc = Nowcaster()
    reports, source = fetch_reports()
    prepared = nc.features_from_reports(reports)
    res = run_nowcast(nc, source=source, prepared=prepared)
    grid = prepared[0]
    t = grid.index[grid["vis_m"].notna().to_numpy()][-1]
    added = log.record(t, {"fog": res["fog"], "rvr": res["rvr"]}, mode="live")
    verified = log.verify(grid)

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "app" / "static", out / "static")
    shutil.copy(ROOT / "app" / "static" / "index.html", out / "index.html")
    (out / ".nojekyll").write_text("")
    api = out / "api"
    api.mkdir(parents=True)
    res["error"] = None
    res["labels"] = {k: {"en": v[0], "tr": v[1]} for k, v in FEATURE_LABELS.items()}
    (api / "nowcast").write_text(json.dumps(res), encoding="utf-8")
    (api / "log").write_text(json.dumps(log_json(log)), encoding="utf-8")
    (api / "verification").write_text(json.dumps(log.summary()), encoding="utf-8")
    print(json.dumps({"published": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      "issue_time": res["issue_time"], "source": source, "alert": res["alert"],
                      "added": added, "verified": verified}))


if __name__ == "__main__":
    main()
