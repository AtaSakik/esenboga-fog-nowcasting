"""LTAC low-visibility early-warning web application (FastAPI).

Run:  uvicorn app.server:app --port 8000      (from the project root)
Then open http://localhost:8000
"""
from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from esenboga.inference import Nowcaster, fetch_reports, run_nowcast  # noqa: E402
from esenboga.labels import FEATURE_LABELS  # noqa: E402
from live_log import LiveLog, backfill  # noqa: E402

STATIC = ROOT / "app" / "static"
CACHE_S = 300
LOOP_S = 600
STATE: dict = {"result": None, "fetched": None, "error": None}


def refresh() -> dict:
    nc: Nowcaster = STATE["nc"]
    reports, source = fetch_reports()
    prepared = nc.features_from_reports(reports)
    res = run_nowcast(nc, source=source, prepared=prepared)
    log: LiveLog = STATE["log"]
    grid = prepared[0]
    t = grid.index[grid["vis_m"].notna().to_numpy()][-1]
    log.record(t, {"fog": res["fog"], "rvr": res["rvr"]}, mode="live")
    log.verify(grid)
    STATE.update(result=res, fetched=datetime.now(timezone.utc), error=None)
    return res


async def loop() -> None:
    while True:
        try:
            await asyncio.to_thread(refresh)
        except Exception as exc:  # network outage: keep serving the last result
            STATE["error"] = repr(exc)
        await asyncio.sleep(LOOP_S)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    STATE["nc"] = Nowcaster()
    STATE["log"] = LiveLog()
    if STATE["log"].frame().empty:
        try:
            await asyncio.to_thread(backfill, STATE["nc"], STATE["log"], 72)
        except Exception as exc:
            STATE["error"] = repr(exc)
    task = asyncio.create_task(loop())
    yield
    task.cancel()


app = FastAPI(title="LTAC Fog Nowcast", version="1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/nowcast")
async def nowcast(refresh_now: bool = Query(False, alias="refresh")):
    age = None if STATE["fetched"] is None else (datetime.now(timezone.utc) - STATE["fetched"]).total_seconds()
    if refresh_now or STATE["result"] is None or age is None or age > CACHE_S:
        try:
            await asyncio.to_thread(refresh)
        except Exception as exc:
            STATE["error"] = repr(exc)
            if STATE["result"] is None:
                return JSONResponse({"error": STATE["error"]}, status_code=503)
    res = dict(STATE["result"])
    res["error"] = STATE["error"]
    res["labels"] = {k: {"en": v[0], "tr": v[1]} for k, v in FEATURE_LABELS.items()}
    return res


@app.get("/api/log")
def prediction_log(hours: float = 72.0, horizon: int = 3):
    df = STATE["log"].frame(hours)
    if df.empty:
        return []
    df = df[(df["target"] == "fog") & (df["horizon"] == horizon)].sort_values("valid_time")
    return [{"valid_time": v.isoformat(), "issue_time": i.isoformat(), "p": p, "thr": th,
             "observed": None if o != o else int(o), "obs_vis": None if ov != ov else ov,
             "mode": m}
            for v, i, p, th, o, ov, m in zip(df["valid_time"], df["issue_time"], df["prob"],
                                             df["threshold"], df["observed"], df["obs_vis"],
                                             df["mode"])]


@app.get("/api/verification")
def verification():
    return STATE["log"].summary()


@app.get("/api/health")
def health():
    return {"ok": STATE["result"] is not None, "error": STATE["error"],
            "fetched": None if STATE["fetched"] is None else STATE["fetched"].isoformat(),
            "models": [f"{t}_{h}h" for (t, h) in sorted(STATE["nc"].models)]}
