"""FastAPI backend — Rockfall Prediction & Early Warning System.

Run (from backend/):  uvicorn app.main:app --reload --port 8000
Docs:                 http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .agent import TICK_SECONDS, agent
from .data.mines import MINES, MONTHLY_NORMALS
from .ml.predictor import assess, load_model, model_info
from .report import build_pdf
from .schemas import AssessmentInput

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_model()  # trains automatically on first run if no model file exists
    task = asyncio.create_task(agent.run())
    yield
    agent.running = False
    task.cancel()


app = FastAPI(title="Rockfall Prediction & Early Warning API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _mine(mine_id: str) -> dict:
    for m in MINES:
        if m["id"] == mine_id:
            return m
    raise HTTPException(404, f"Unknown mine '{mine_id}'")


@app.get("/api/health")
def health():
    return {"status": "ok", "agent_running": agent.running, "agent_ticks": agent.ticks, "tick_seconds": TICK_SECONDS}


@app.get("/api/mines")
def list_mines():
    """All monitored mines with their latest risk score and zone scores."""
    return agent.summary()


@app.get("/api/mines/{mine_id}/assessment")
def mine_assessment(mine_id: str):
    _mine(mine_id)
    a = dict(agent.assessments[mine_id])
    a["history"] = list(agent.history[mine_id])
    return a


@app.get("/api/assessments")
def all_assessments():
    return [agent.assessments[m["id"]] for m in MINES]


@app.post("/api/predict")
def predict(payload: AssessmentInput):
    """Run the hybrid model on custom readings (used by 'New Assessment')."""
    data = payload.model_dump()
    a = assess(data)
    a["mine"] = {"id": "custom", "name": data["mine_name"], "location": data["location"]}
    return a


@app.get("/api/mines/{mine_id}/rainfall")
def rainfall_trend(mine_id: str):
    """Rainfall of the last 12 months vs. long-term normal."""
    _mine(mine_id)
    normals = MONTHLY_NORMALS[mine_id]
    rng = random.Random(mine_id)
    today = date.today()
    out = []
    for i in range(11, -1, -1):
        mi = (today.month - 1 - i) % 12
        year = today.year - (1 if today.month - 1 - i < 0 else 0)
        actual = max(0.0, normals[mi] * rng.uniform(0.55, 1.5))
        out.append({"month": f"{MONTHS[mi]} {str(year)[2:]}", "rainfall": round(actual, 1), "normal": normals[mi]})
    return out


@app.get("/api/alerts")
def alerts(limit: int = 50):
    return list(agent.alerts)[:limit]


@app.get("/api/model/info")
def model_details():
    return model_info()


@app.get("/api/mines/{mine_id}/report")
def mine_report(mine_id: str):
    m = _mine(mine_id)
    pdf = build_pdf(agent.assessments[mine_id], m["name"], f"{m['location']}, {m['state']}")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="rockfall_report_{mine_id}.pdf"'})


@app.post("/api/report")
def custom_report(payload: AssessmentInput):
    data = payload.model_dump()
    pdf = build_pdf(assess(data), data["mine_name"], data["location"])
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="rockfall_report_custom.pdf"'})


@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await ws.accept()
    agent.clients.add(ws)
    await ws.send_json({"type": "tick", "mines": agent.summary()})
    try:
        while True:
            await ws.receive_text()  # keep-alive; client may send pings
    except WebSocketDisconnect:
        pass
    finally:
        agent.clients.discard(ws)
