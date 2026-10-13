"""Temporal smoothing for multi-activity detections to eliminate flicker."""

import time
from typing import Dict, List, Optional, Set

from app.config import SMOOTHING_WINDOW_SEC


class ActivitySmoother:
    """Smooths categorical posture states over a sliding time window (single activity)."""

    def __init__(self, window_sec: float = SMOOTHING_WINDOW_SEC, initial_state: str = "away"):
        self.window_sec = window_sec
        self.current_state: str = initial_state
        self.candidate_state: Optional[str] = initial_state
        self.candidate_since: float = time.time()

    def update(self, raw_state: str, now: Optional[float] = None) -> str:
        """Update with a new raw detection reading and return the smoothed state."""
        if now is None:
            now = time.time()

        if raw_state == self.current_state:
            self.candidate_state = raw_state
            self.candidate_since = now
            return self.current_state

        if raw_state != self.candidate_state:
            self.candidate_state = raw_state
            self.candidate_since = now
        elif (now - self.candidate_since) >= self.window_sec:
            self.current_state = raw_state

        return self.current_state

    def reset(self, state: str = "away") -> None:
        """Reset the smoother to an initial state."""
        self.current_state = state
        self.candidate_state = state
        self.candidate_since = time.time()


class MultiActivitySmoother:
    """Smooths concurrent activities over a sliding time window.

    - Posture (sitting, standing, away, undefined) is mutually exclusive and
      transitions after candidate stability >= window_sec.
    - Object activities (laptop, book/paper, phone in hand) independently turn
      ON after being detected continuously for >= window_sec, and turn OFF
      after being absent continuously for >= window_sec.
    """

    KNOWN_OBJECTS = {"laptop", "book/paper", "phone in hand"}

    def __init__(
        self,
        window_sec: float = SMOOTHING_WINDOW_SEC,
        initial_posture: str = "away",
        initial_state: Optional[str] = None,
    ):
        self.window_sec = window_sec
        posture = initial_state if initial_state is not None else initial_posture

        # Posture state
        self.current_posture: str = posture
        self.candidate_posture: Optional[str] = posture
        self.candidate_posture_since: float = time.time()

        # Object states: object_name -> bool (is_active)
        self.active_objects: Set[str] = set()

        # Object pending transitions: object_name -> {"target": bool, "since": float}
        self.object_pending: Dict[str, Dict[str, float]] = {}

    def update(
        self,
        raw_posture: str,
        raw_objects: Optional[Set[str]] = None,
        now: Optional[float] = None,
    ) -> List[str]:
        """Update with latest raw posture and detected objects.

        Returns list of smoothed active activities (e.g. ["sitting", "laptop"]).
        """
        if raw_objects is None:
            raw_objects = set()

        if now is None:
            now = time.time()

        # 1. Update Posture (mutually exclusive)
        if raw_posture == self.current_posture:
            self.candidate_posture = raw_posture
            self.candidate_posture_since = now
        else:
            if raw_posture != self.candidate_posture:
                self.candidate_posture = raw_posture
                self.candidate_posture_since = now
            elif (now - self.candidate_posture_since) >= self.window_sec:
                self.current_posture = raw_posture

        # 2. Update Object activities (independent debounce)
        candidate_pool = self.KNOWN_OBJECTS | raw_objects

        for obj in candidate_pool:
            is_detected = obj in raw_objects
            is_currently_active = obj in self.active_objects

            if is_detected == is_currently_active:
                self.object_pending.pop(obj, None)
            else:
                pending = self.object_pending.get(obj)
                if pending is None or pending["target"] != is_detected:
                    self.object_pending[obj] = {"target": is_detected, "since": now}
                elif (now - pending["since"]) >= self.window_sec:
                    if is_detected:
                        self.active_objects.add(obj)
                    else:
                        self.active_objects.discard(obj)
                    self.object_pending.pop(obj, None)

        # 3. Assemble combined result
        if self.current_posture == "away":
            return ["away"]

        result = [self.current_posture]
        for obj in sorted(self.active_objects):
            result.append(obj)

        return result

    def reset(self, posture: str = "away") -> None:
        """Reset smoother to initial empty state."""
        self.current_posture = posture
        self.candidate_posture = posture
        self.candidate_posture_since = time.time()
        self.active_objects.clear()
        self.object_pending.clear()
