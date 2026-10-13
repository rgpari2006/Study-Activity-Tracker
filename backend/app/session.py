"""Session state machine, timer logic, storage persistence, and tracker orchestration."""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any, List, Optional

from app.storage.db import DatabaseManager
from app.storage.recorder import CameraActivityRecorder
from app.tracking.tracker import WindowTrackingService


class SessionState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SessionManager:
    """Manages study session lifecycle, camera, window tracking, and database persistence."""

    def __init__(
        self,
        camera,
        window_tracker: Optional[WindowTrackingService] = None,
        db: Optional[DatabaseManager] = None,
        activity_recorder: Optional[CameraActivityRecorder] = None,
    ) -> None:
        self._camera = camera
        self._window_tracker = window_tracker if window_tracker is not None else WindowTrackingService()
        self._db = db if db is not None else DatabaseManager()
        self._activity_recorder = activity_recorder if activity_recorder is not None else CameraActivityRecorder()

        self._state = SessionState.STOPPED
        self._planned_duration_sec: int = 0
        self._start_time: float = 0.0
        self._pause_start: float = 0.0
        self._paused_total: float = 0.0
        self._session_id: Optional[int] = None

        self._ticker_thread: Optional[threading.Thread] = None
        self._ticker_running = False
        self._lock = threading.Lock()

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def session_id(self) -> Optional[int]:
        return self._session_id

    # ---- Commands ----

    def start(self, planned_duration_sec: int) -> int:
        if self._state != SessionState.STOPPED:
            raise ValueError("Session already active")

        self._planned_duration_sec = planned_duration_sec
        self._start_time = time.time()
        self._pause_start = 0.0
        self._paused_total = 0.0
        self._state = SessionState.RUNNING

        # 1. Create session in database
        self._session_id = self._db.create_session(self._start_time, self._planned_duration_sec)

        # 2. Start hardware and services
        self._camera.start()
        self._window_tracker.start()

        # 3. Start activity recorder
        initial_acts = self._camera.get_current_activities()
        self._activity_recorder.start(initial_acts, now=self._start_time)

        # 4. Start periodic recorder ticker
        self._start_ticker()

        return self._session_id

    def pause(self) -> None:
        if self._state != SessionState.RUNNING:
            raise ValueError("Session is not running")

        now = time.time()
        self._pause_start = now
        self._state = SessionState.PAUSED

        self._stop_ticker()
        self._window_tracker.pause()
        self._activity_recorder.pause(now=now)

    def resume(self) -> None:
        if self._state != SessionState.PAUSED:
            raise ValueError("Session is not paused")

        now = time.time()
        self._paused_total += now - self._pause_start
        self._pause_start = 0.0
        self._state = SessionState.RUNNING

        self._window_tracker.resume()
        self._activity_recorder.resume(self._camera.get_current_activities(), now=now)
        self._start_ticker()

    def stop(self) -> Optional[int]:
        if self._state == SessionState.STOPPED:
            raise ValueError("No active session")

        now = time.time()
        if self._state == SessionState.PAUSED:
            self._paused_total += now - self._pause_start

        self._stop_ticker()
        self._camera.stop()
        self._window_tracker.stop()

        # Finalize recorded events
        activity_events = self._activity_recorder.stop(now=now)
        app_events = self._window_tracker.get_intervals()

        finished_id = self._session_id
        if finished_id is not None:
            # Persist to SQLite
            self._db.finish_session(finished_id, now, self._paused_total)
            self._db.insert_activity_events(finished_id, activity_events)
            self._db.insert_app_events(finished_id, app_events)

        self._state = SessionState.STOPPED
        self._session_id = None
        return finished_id

    # ---- Queries ----

    def elapsed_sec(self) -> float:
        """Compute elapsed seconds excluding paused time."""
        if self._state == SessionState.STOPPED:
            return 0.0
        now = time.time()
        total = now - self._start_time - self._paused_total
        if self._state == SessionState.PAUSED:
            total -= now - self._pause_start
        return max(total, 0.0)

    def get_activities(self) -> List[str]:
        """Fetch current detected activities from camera if running."""
        if self._state in (SessionState.RUNNING, SessionState.PAUSED):
            return self._camera.get_current_activities()
        return []

    def get_active_app(self) -> Optional[dict[str, str]]:
        """Fetch current active foreground window info if running."""
        if self._state == SessionState.RUNNING:
            return self._window_tracker.get_current_window()
        return None

    def get_app_intervals(self) -> List[dict[str, Any]]:
        """Fetch recorded application intervals."""
        return self._window_tracker.get_intervals()

    def get_state(self) -> dict[str, Any]:
        """Return the payload pushed over WebSocket."""
        acts = self.get_activities()
        if self._state == SessionState.RUNNING:
            self._activity_recorder.update(acts)

        return {
            "session_state": self._state.value,
            "session_id": self._session_id,
            "elapsed_sec": round(self.elapsed_sec(), 1),
            "planned_duration_sec": self._planned_duration_sec,
            "current_activities": acts,
            "active_app": self.get_active_app(),
        }

    # ---- Internal Helpers ----

    def _start_ticker(self) -> None:
        with self._lock:
            self._ticker_running = True
            self._ticker_thread = threading.Thread(target=self._ticker_loop, daemon=True)
            self._ticker_thread.start()

    def _stop_ticker(self) -> None:
        with self._lock:
            self._ticker_running = False
            if self._ticker_thread is not None:
                self._ticker_thread.join(timeout=1.0)
                self._ticker_thread = None

    def _ticker_loop(self) -> None:
        """Periodic loop updating the activity recorder once per second."""
        while self._ticker_running and self._state == SessionState.RUNNING:
            acts = self._camera.get_current_activities()
            self._activity_recorder.update(acts)
            time.sleep(1.0)
