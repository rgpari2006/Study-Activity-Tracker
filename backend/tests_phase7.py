"""Tests for Phase 7: Accuracy tuning, threshold boundaries, and Hard Rules verification."""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from app.camera.detector import PoseDetector, StudyActivityDetector
from app.camera.smoothing import MultiActivitySmoother
from app.config import CONFIDENCE_THRESHOLD, PHONE_PROXIMITY_RATIO


class TestAccuracyAndThresholds(unittest.TestCase):
    def test_pose_confidence_threshold_fallback(self):
        detector = PoseDetector(confidence_threshold=0.5)

        # Mock YOLO inference returning confidence 0.35 (< 0.5)
        mock_box = MagicMock()
        mock_box.__len__.return_value = 1
        mock_box.conf.cpu().numpy.return_value = np.array([0.35])
        mock_box.xyxy.cpu().numpy.return_value = np.array([[10, 10, 100, 100]])

        mock_result = MagicMock()
        mock_result.boxes = mock_box
        mock_result.keypoints = None
        mock_result.plot.return_value = np.zeros((200, 200, 3), dtype=np.uint8)

        with patch.object(detector, "model", return_value=[mock_result]):
            frame = np.zeros((200, 200, 3), dtype=np.uint8)
            label, conf, annotated = detector.detect(frame)

            # Hard Rule 4: If detection is not confident (< 0.5), record as Undefined
            self.assertEqual(label, "undefined")
            self.assertAlmostEqual(conf, 0.35)

    def test_allowed_labels_and_hard_rules_compliance(self):
        """Verify detector labels strictly conform to the defined set and contain no judgmental words."""
        allowed_labels = {
            "sitting",
            "standing",
            "away",
            "laptop",
            "book/paper",
            "phone in hand",
            "undefined",
        }
        forbidden_judgmental_words = {
            "productive",
            "wasted",
            "distracted",
            "focused",
            "studying",
        }

        detector = StudyActivityDetector()
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        posture, objects, _ = detector.detect(blank)

        all_detected = {posture} | objects
        for label in all_detected:
            self.assertIn(label, allowed_labels)
            for forbidden in forbidden_judgmental_words:
                self.assertNotIn(forbidden, label.lower())

    def test_phone_proximity_ratio_configuration(self):
        detector = StudyActivityDetector(phone_proximity_ratio=0.25)
        self.assertEqual(detector.phone_proximity_ratio, PHONE_PROXIMITY_RATIO)


class TestSmootherEdgeCases(unittest.TestCase):
    def test_rapid_flicker_rejection(self):
        smoother = MultiActivitySmoother(window_sec=2.0, initial_posture="sitting")

        # Rapidly flip between sitting, standing, and undefined every 0.2s for 1.8s
        t = 100.0
        for i in range(9):
            candidate = "standing" if i % 2 == 0 else "undefined"
            res = smoother.update(candidate, set(), now=t + i * 0.2)
            # Must remain sitting because no candidate held for >= 2.0s
            self.assertEqual(res, ["sitting"])

        # At t = 102.0s, candidate holds steady for 2.0s
        t_stable = 102.0
        smoother.update("standing", set(), now=t_stable)
        res = smoother.update("standing", set(), now=t_stable + 2.0)
        self.assertEqual(res, ["standing"])


if __name__ == "__main__":
    unittest.main()
