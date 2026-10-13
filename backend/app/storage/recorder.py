"""Recorder for tracking concurrent camera activity intervals."""

import threading
import time
from typing import Any, Dict, List, Optional, Set


class CameraActivityRecorder:
    """Records concurrent intervals for camera activities (sitting, laptop, book, etc.).

    Each activity label maintains its own independent start and end times.
    Pausing or stopping the session closes active intervals, ensuring paused
    time is not included in recorded activity durations.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._open_intervals: Dict[str, Dict[str, Any]] = {}
        self._completed_intervals: List[Dict[str, Any]] = []

    def start(self, initial_activities: Optional[List[str]] = None, now: Optional[float] = None) -> None:
        """Start tracking for a new session."""
        if now is None:
            now = time.time()

        with self._lock:
            self._open_intervals.clear()
            self._completed_intervals.clear()
            if initial_activities:
                for act in initial_activities:
                    self._open_intervals[act] = {
                        "activity_label": act,
                        "start_time": now,
                        "end_time": now,
                    }

    def update(self, current_activities: List[str], now: Optional[float] = None) -> None:
        """Update with latest list of active activities."""
        if now is None:
            now = time.time()

        active_set: Set[str] = set(current_activities)

        with self._lock:
            # 1. Update continuing activities or close deactivated ones
            current_open_labels = list(self._open_intervals.keys())
            for label in current_open_labels:
                if label in active_set:
                    # Still active: extend end_time
                    self._open_intervals[label]["end_time"] = now
                else:
                    # Deactivated: close and save interval
                    interval = self._open_intervals.pop(label)
                    interval["end_time"] = now
                    self._completed_intervals.append(interval)

            # 2. Open newly activated activities
            for label in active_set:
                if label not in self._open_intervals:
                    self._open_intervals[label] = {
                        "activity_label": label,
                        "start_time": now,
                        "end_time": now,
                    }

    def pause(self, now: Optional[float] = None) -> None:
        """Seal all open intervals upon pausing."""
        if now is None:
            now = time.time()

        with self._lock:
            for interval in self._open_intervals.values():
                interval["end_time"] = now
                self._completed_intervals.append(interval)
            self._open_intervals.clear()

    def resume(self, current_activities: Optional[List[str]] = None, now: Optional[float] = None) -> None:
        """Resume tracking after a pause."""
        if now is None:
            now = time.time()

        with self._lock:
            self._open_intervals.clear()
            if current_activities:
                for act in current_activities:
                    self._open_intervals[act] = {
                        "activity_label": act,
                        "start_time": now,
                        "end_time": now,
                    }

    def stop(self, now: Optional[float] = None) -> List[Dict[str, Any]]:
        """Stop tracking, seal all open intervals, and return the complete list of events."""
        if now is None:
            now = time.time()

        with self._lock:
            for interval in self._open_intervals.values():
                interval["end_time"] = now
                self._completed_intervals.append(interval)
            self._open_intervals.clear()
            return [dict(it) for it in self._completed_intervals]

    def get_events(self) -> List[Dict[str, Any]]:
        """Return all completed and currently open intervals."""
        with self._lock:
            result = [dict(it) for it in self._completed_intervals]
            for interval in self._open_intervals.values():
                result.append(dict(interval))
            return result
