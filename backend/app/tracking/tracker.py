"""Service for sampling active foreground windows and merging consecutive samples into intervals."""

import sys
import threading
import time
from typing import Dict, List, Optional

from app.tracking.base import BaseWindowTracker, WindowInfo


def get_default_tracker() -> BaseWindowTracker:
    """Instantiate platform-specific window tracker."""
    if sys.platform == "win32":
        from app.tracking.windows import WindowsWindowTracker
        return WindowsWindowTracker()
    else:
        # Fallback dummy tracker for non-Windows environments
        class DummyTracker(BaseWindowTracker):
            def get_active_window(self) -> Optional[WindowInfo]:
                return None
        return DummyTracker()


class WindowTrackingService:
    """Periodically samples the active window and merges consecutive samples into intervals."""

    def __init__(
        self,
        tracker: Optional[BaseWindowTracker] = None,
        sample_interval_sec: float = 1.0,
    ):
        self._tracker = tracker if tracker is not None else get_default_tracker()
        self._sample_interval_sec = sample_interval_sec
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        self._current_window: Optional[WindowInfo] = None
        self._active_interval: Optional[Dict[str, any]] = None
        self._completed_intervals: List[Dict[str, any]] = []

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the window tracking background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._current_window = None
            self._active_interval = None
            self._completed_intervals = []

        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Pause tracking and close current open interval."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        with self._lock:
            self._close_active_interval(time.time())
            self._current_window = None

    def resume(self) -> None:
        """Resume tracking background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._current_window = None
            self._active_interval = None

        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop tracking and finalize all intervals."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        with self._lock:
            self._close_active_interval(time.time())
            self._current_window = None

    def get_current_window(self) -> Optional[WindowInfo]:
        """Return the latest active foreground window info."""
        with self._lock:
            if self._current_window is not None:
                return dict(self._current_window)
            return None

    def get_intervals(self) -> List[Dict[str, any]]:
        """Return all recorded app intervals (completed + currently active snapshot)."""
        with self._lock:
            intervals = [dict(it) for it in self._completed_intervals]
            if self._active_interval is not None:
                intervals.append(dict(self._active_interval))
            return intervals

    def sample_once(self, now: Optional[float] = None) -> Optional[WindowInfo]:
        """Take a single sample and update interval aggregation. Useful for testing and manual stepping."""
        if now is None:
            now = time.time()

        window = self._tracker.get_active_window()
        with self._lock:
            self._current_window = window

            if window is None:
                self._close_active_interval(now)
            else:
                name = window["name"]
                title = window["title"]

                if (
                    self._active_interval is not None
                    and self._active_interval["app_name"] == name
                    and self._active_interval["window_title"] == title
                ):
                    # Same window continues: extend end_time
                    self._active_interval["end_time"] = now
                else:
                    # Switched to a new window: close previous and start new
                    self._close_active_interval(now)
                    self._active_interval = {
                        "app_name": name,
                        "window_title": title,
                        "start_time": now,
                        "end_time": now,
                    }

            return window

    def _close_active_interval(self, end_time: float) -> None:
        """Close and store the currently open interval (must be called with _lock acquired)."""
        if self._active_interval is not None:
            self._active_interval["end_time"] = end_time
            self._completed_intervals.append(self._active_interval)
            self._active_interval = None

    def _sample_loop(self) -> None:
        """Background loop querying the foreground window."""
        while self._running:
            self.sample_once()
            time.sleep(self._sample_interval_sec)
