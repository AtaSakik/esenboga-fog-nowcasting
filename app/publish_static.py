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
from esenboga.inference import Nowcaster  # noqa: E402
from esenboga.labels import LABELS_JSON  # noqa: E402
from live_log import LiveLog, run_cycle  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    log = LiveLog(Path(args.db))
    res, counts = run_cycle(Nowcaster(), log)

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "app" / "static", out / "static")
    shutil.copy(ROOT / "app" / "static" / "index.html", out / "index.html")
    (out / ".nojekyll").write_text("")
    api = out / "api"
    api.mkdir(parents=True)
    res["error"] = None
    res["labels"] = LABELS_JSON
    (api / "nowcast").write_text(json.dumps(res), encoding="utf-8")
    (api / "log").write_text(json.dumps(log.forecasts_json()), encoding="utf-8")
    (api / "verification").write_text(json.dumps(log.summary()), encoding="utf-8")
    print(json.dumps({"published": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                      "issue_time": res["issue_time"], "source": res["source"],
                      "alert": res["alert"], **counts}))


if __name__ == "__main__":
    main()
