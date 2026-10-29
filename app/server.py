"""LTAC low-visibility early-warning web application (FastAPI).

Run:  uvicorn app.server:app --port 8000      (from the project root)
Then open http://localhost:8000
"""
from __future__ import annotations

import asyncio
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
from esenboga.inference import Nowcaster  # noqa: E402
from esenboga.labels import LABELS_JSON  # noqa: E402
from live_log import LiveLog, backfill, run_cycle  # noqa: E402

STATIC = ROOT / "app" / "static"
CACHE_S = 300
LOOP_S = 600
MIN_REFRESH_S = 60          # requests arriving together share one upstream fetch
STATE: dict = {"result": None, "fetched": None, "error": None}
REFRESH_LOCK = threading.Lock()


def _age_s() -> float | None:
    return None if STATE["fetched"] is None else (datetime.now(timezone.utc) - STATE["fetched"]).total_seconds()


def refresh() -> dict:
    """Run one live cycle; concurrent callers wait for the cycle in progress instead of
    starting their own (one fetch, one set of SQLite writes)."""
    with REFRESH_LOCK:
        age = _age_s()
        if STATE["result"] is not None and age is not None and age < MIN_REFRESH_S:
            return STATE["result"]
        res, _, _ = run_cycle(STATE["nc"], STATE["log"])
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
    age = _age_s()
    if refresh_now or STATE["result"] is None or age is None or age > CACHE_S:
        try:
            await asyncio.to_thread(refresh)
        except Exception as exc:
            STATE["error"] = repr(exc)
            if STATE["result"] is None:
                return JSONResponse({"error": STATE["error"]}, status_code=503)
    res = dict(STATE["result"])
    res["error"] = STATE["error"]
    res["labels"] = LABELS_JSON
    return res


@app.get("/api/log")
def prediction_log(hours: float = 72.0, horizon: int = 3):
    return STATE["log"].forecasts_json(hours, horizon)


@app.get("/api/verification")
def verification():
    return STATE["log"].summary()


@app.get("/api/health")
def health():
    return {"ok": STATE["result"] is not None, "error": STATE["error"],
            "fetched": None if STATE["fetched"] is None else STATE["fetched"].isoformat(),
            "models": [f"{t}_{h}h" for (t, h) in sorted(STATE["nc"].models)]}
