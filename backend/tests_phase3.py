import unittest
from unittest.mock import MagicMock
import numpy as np

from app.camera.smoothing import MultiActivitySmoother
from app.camera.detector import StudyActivityDetector
from app.session import SessionManager


class TestMultiActivitySmoother(unittest.TestCase):
    def setUp(self):
        self.smoother = MultiActivitySmoother(window_sec=2.0, initial_posture="sitting")

    def test_multi_activity_activation(self):
        t0 = 100.0
        # Initially only sitting is active
        res = self.smoother.update("sitting", set(), now=t0)
        self.assertEqual(res, ["sitting"])

        # Laptop observed at t0
        res = self.smoother.update("sitting", {"laptop"}, now=t0)
        self.assertEqual(res, ["sitting"])  # not yet 2s

        # At t0 + 1.0s: still only sitting
        res = self.smoother.update("sitting", {"laptop"}, now=t0 + 1.0)
        self.assertEqual(res, ["sitting"])

        # At t0 + 2.0s: laptop transitions to ON!
        res = self.smoother.update("sitting", {"laptop"}, now=t0 + 2.0)
        self.assertEqual(res, ["sitting", "laptop"])

    def test_concurrent_objects_independent_timers(self):
        t0 = 100.0
        # Laptop already active
        self.smoother.active_objects.add("laptop")

        # Now phone in hand appears at t0
        self.smoother.update("sitting", {"laptop", "phone in hand"}, now=t0)
        # At t0 + 1.0s: phone not yet active
        res = self.smoother.update("sitting", {"laptop", "phone in hand"}, now=t0 + 1.0)
        self.assertEqual(res, ["sitting", "laptop"])

        # At t0 + 2.0s: phone turns ON alongside laptop
        res = self.smoother.update("sitting", {"laptop", "phone in hand"}, now=t0 + 2.0)
        self.assertEqual(res, ["sitting", "laptop", "phone in hand"])

    def test_object_deactivation_delay(self):
        t0 = 100.0
        self.smoother.active_objects.add("phone in hand")

        # Phone is removed at t0
        res = self.smoother.update("sitting", set(), now=t0)
        self.assertEqual(res, ["sitting", "phone in hand"])  # Still ON

        # 1.5s later: still ON
        res = self.smoother.update("sitting", set(), now=t0 + 1.5)
        self.assertEqual(res, ["sitting", "phone in hand"])

        # 2.0s later: turns OFF
        res = self.smoother.update("sitting", set(), now=t0 + 2.0)
        self.assertEqual(res, ["sitting"])

    def test_flicker_rejection(self):
        t0 = 100.0
        # Brief 0.4s false positive for book/paper
        self.smoother.update("sitting", {"book/paper"}, now=t0)
        self.smoother.update("sitting", {"book/paper"}, now=t0 + 0.4)
        # Disappears
        res = self.smoother.update("sitting", set(), now=t0 + 0.5)
        self.assertEqual(res, ["sitting"])

        # At t0 + 2.5: book/paper never activated
        res = self.smoother.update("sitting", set(), now=t0 + 2.5)
        self.assertEqual(res, ["sitting"])

    def test_away_suppresses_objects(self):
        self.smoother.current_posture = "away"
        self.smoother.active_objects.add("laptop")
        res = self.smoother.update("away", {"laptop"}, now=200.0)
        self.assertEqual(res, ["away"])


class TestStudyActivityDetector(unittest.TestCase):
    def test_blank_frame_away(self):
        detector = StudyActivityDetector()
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        posture, objects, annotated = detector.detect(blank)

        self.assertEqual(posture, "away")
        self.assertEqual(objects, set())
        self.assertEqual(annotated.shape, blank.shape)


class TestSessionConcurrentActivities(unittest.TestCase):
    def test_concurrent_payload(self):
        mock_camera = MagicMock()
        mock_camera.get_current_activities.return_value = ["sitting", "laptop", "phone in hand"]

        sm = SessionManager(mock_camera)
        sm.start(planned_duration_sec=1800)

        state = sm.get_state()
        self.assertEqual(state["current_activities"], ["sitting", "laptop", "phone in hand"])


if __name__ == "__main__":
    unittest.main()
