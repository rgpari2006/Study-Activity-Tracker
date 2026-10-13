import time
import unittest
from unittest.mock import MagicMock
import numpy as np

from app.camera.smoothing import ActivitySmoother
from app.camera.detector import PoseDetector
from app.session import SessionManager, SessionState


class TestActivitySmoother(unittest.TestCase):
    def test_initial_state(self):
        smoother = ActivitySmoother(window_sec=2.0, initial_state="away")
        self.assertEqual(smoother.current_state, "away")

    def test_smoothing_debounce(self):
        t0 = 1000.0
        smoother = ActivitySmoother(window_sec=2.0, initial_state="away")

        # First observation of sitting at t0: should not transition yet
        res = smoother.update("sitting", now=t0)
        self.assertEqual(res, "away")

        # 1.0 second later: still away
        res = smoother.update("sitting", now=t0 + 1.0)
        self.assertEqual(res, "away")

        # 1.9 seconds later: still away
        res = smoother.update("sitting", now=t0 + 1.9)
        self.assertEqual(res, "away")

        # Exactly 2.0 seconds later: should transition to sitting!
        res = smoother.update("sitting", now=t0 + 2.0)
        self.assertEqual(res, "sitting")
        self.assertEqual(smoother.current_state, "sitting")

    def test_smoothing_flicker_rejection(self):
        t0 = 1000.0
        smoother = ActivitySmoother(window_sec=2.0, initial_state="sitting")

        # Temporary 0.5s glitch to standing, then back to sitting
        smoother.update("standing", now=t0)
        smoother.update("standing", now=t0 + 0.5)
        res = smoother.update("sitting", now=t0 + 0.6)
        self.assertEqual(res, "sitting")

        # Sitting remains stable
        res = smoother.update("sitting", now=t0 + 2.0)
        self.assertEqual(res, "sitting")


class TestPoseDetector(unittest.TestCase):
    def setUp(self):
        self.detector = PoseDetector(confidence_threshold=0.5)

    def test_blank_frame_returns_away(self):
        # A blank black image contains no persons
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        label, conf, annotated = self.detector.detect(blank_frame)

        self.assertEqual(label, "away")
        self.assertEqual(conf, 0.0)
        self.assertEqual(annotated.shape, blank_frame.shape)


class TestSessionActivitiesIntegration(unittest.TestCase):
    def test_session_activities(self):
        mock_camera = MagicMock()
        mock_camera.get_current_activities.return_value = ["sitting"]

        sm = SessionManager(mock_camera)
        # When stopped, activities should be empty
        self.assertEqual(sm.get_state()["current_activities"], [])

        # When running, should return camera activities
        sm.start(planned_duration_sec=300)
        state = sm.get_state()
        self.assertEqual(state["current_activities"], ["sitting"])

        # When paused, should retain activities
        sm.pause()
        self.assertEqual(sm.get_state()["current_activities"], ["sitting"])

        # When stopped, clears
        sm.stop()
        self.assertEqual(sm.get_state()["current_activities"], [])


if __name__ == "__main__":
    unittest.main()
