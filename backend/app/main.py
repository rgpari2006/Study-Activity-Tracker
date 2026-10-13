"""FastAPI application — routes, WebSocket, MJPEG feed, persistence, and analytics."""

import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.analytics.service import AnalyticsService
from app.camera.capture import CameraThread, mjpeg_stream
from app.config import WS_PUSH_INTERVAL_SEC
from app.session import SessionManager
from app.storage.db import DatabaseManager

app = FastAPI(title="Study Activity Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
db = DatabaseManager()
analytics_service = AnalyticsService(db)
camera = CameraThread()
session_manager = SessionManager(camera=camera, db=db)


# ---- Request models ----

class StartRequest(BaseModel):
    planned_duration_sec: int


# ---- REST routes: Sessions ----

@app.post("/sessions/start")
def start_session(body: StartRequest):
    session_id = session_manager.start(body.planned_duration_sec)
    return {"status": "started", "session_id": session_id}


@app.post("/sessions/pause")
def pause_session():
    session_manager.pause()
    return {"status": "paused"}


@app.post("/sessions/resume")
def resume_session():
    session_manager.resume()
    return {"status": "resumed"}


@app.post("/sessions/stop")
def stop_session():
    session_id = session_manager.stop()
    return {"status": "stopped", "session_id": session_id}


@app.get("/sessions")
def list_sessions():
    """List all past study sessions."""
    return db.get_sessions()


@app.get("/sessions/{session_id}")
def get_session_details(session_id: int):
    """Retrieve full session details including activity and app intervals."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ---- REST routes: Analytics ----

@app.get("/analytics/summary")
def get_analytics_summary(
    from_time: Optional[float] = Query(None, alias="from"),
    to_time: Optional[float] = Query(None, alias="to"),
):
    """Return aggregated duration summary per camera activity and per application."""
    return analytics_service.get_summary(from_time=from_time, to_time=to_time)


@app.get("/analytics/daily")
def get_analytics_daily(limit: int = 30):
    """Return daily historical session totals and activity distributions."""
    return analytics_service.get_daily(limit_days=limit)


@app.get("/analytics/weekly")
def get_analytics_weekly(limit: int = 12):
    """Return weekly historical session totals."""
    return analytics_service.get_weekly(limit_weeks=limit)


# ---- Camera Stream ----

@app.on_event("startup")
def startup_event():
    import threading
    threading.Thread(target=camera.warmup, daemon=True).start()


@app.get("/video_feed")
def video_feed():
    if not camera.is_running:
        return StreamingResponse(iter([]), media_type="text/plain", status_code=204)
    return StreamingResponse(
        mjpeg_stream(camera),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )



# ---- WebSocket ----

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(session_manager.get_state())
            await asyncio.sleep(WS_PUSH_INTERVAL_SEC)
    except WebSocketDisconnect:
        pass
