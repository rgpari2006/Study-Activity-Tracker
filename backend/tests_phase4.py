import sys
import unittest
from unittest.mock import MagicMock

from app.tracking.base import BaseWindowTracker, WindowInfo
from app.tracking.tracker import WindowTrackingService
from app.session import SessionManager, SessionState


class MockWindowTracker(BaseWindowTracker):
    def __init__(self):
        self.next_window = None

    def get_active_window(self):
        return self.next_window


class TestWindowTrackingService(unittest.TestCase):
    def setUp(self):
        self.mock_tracker = MockWindowTracker()
        self.service = WindowTrackingService(tracker=self.mock_tracker, sample_interval_sec=1.0)

    def test_sample_consecutive_merging(self):
        # Sample 1: Code.exe at t=10.0
        self.mock_tracker.next_window = {"name": "Code.exe", "title": "main.py"}
        win = self.service.sample_once(now=10.0)
        self.assertEqual(win, {"name": "Code.exe", "title": "main.py"})

        intervals = self.service.get_intervals()
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0]["app_name"], "Code.exe")
        self.assertEqual(intervals[0]["start_time"], 10.0)
        self.assertEqual(intervals[0]["end_time"], 10.0)

        # Sample 2: Same window at t=11.0 (merged into same interval)
        self.service.sample_once(now=11.0)
        intervals = self.service.get_intervals()
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0]["start_time"], 10.0)
        self.assertEqual(intervals[0]["end_time"], 11.0)

        # Sample 3: Same window at t=12.0
        self.service.sample_once(now=12.0)
        intervals = self.service.get_intervals()
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0]["end_time"], 12.0)

        # Sample 4: Switched to browser at t=13.0
        self.mock_tracker.next_window = {"name": "chrome.exe", "title": "FastAPI Docs"}
        self.service.sample_once(now=13.0)
        intervals = self.service.get_intervals()
        self.assertEqual(len(intervals), 2)
        # First interval closed
        self.assertEqual(intervals[0]["app_name"], "Code.exe")
        self.assertEqual(intervals[0]["start_time"], 10.0)
        self.assertEqual(intervals[0]["end_time"], 13.0)
        # Second interval started
        self.assertEqual(intervals[1]["app_name"], "chrome.exe")
        self.assertEqual(intervals[1]["start_time"], 13.0)
        self.assertEqual(intervals[1]["end_time"], 13.0)

        # Sample 5: No window (None) at t=14.0
        self.mock_tracker.next_window = None
        self.service.sample_once(now=14.0)
        intervals = self.service.get_intervals()
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[1]["end_time"], 14.0)
        self.assertIsNone(self.service.get_current_window())

    def test_pause_and_resume_lifecycle(self):
        self.mock_tracker.next_window = {"name": "Code.exe", "title": "main.py"}
        self.service.start()
        self.service.sample_once(now=100.0)

        self.service.pause()
        self.assertFalse(self.service.is_running)
        self.assertIsNone(self.service.get_current_window())

        # When resumed, new samples start a fresh interval
        self.mock_tracker.next_window = {"name": "notepad.exe", "title": "notes.txt"}
        self.service.resume()
        self.assertTrue(self.service.is_running)
        self.service.sample_once(now=120.0)

        intervals = self.service.get_intervals()
        self.assertEqual(len(intervals), 2)
        self.assertEqual(intervals[0]["app_name"], "Code.exe")
        self.assertEqual(intervals[1]["app_name"], "notepad.exe")

        self.service.stop()
        self.assertFalse(self.service.is_running)


class TestSessionWindowIntegration(unittest.TestCase):
    def test_session_state_active_app(self):
        mock_camera = MagicMock()
        mock_camera.get_current_activities.return_value = ["sitting"]

        mock_window_tracker = MagicMock()
        mock_window_tracker.get_current_window.return_value = {
            "name": "Code.exe",
            "title": "main.py - VS Code",
        }

        sm = SessionManager(camera=mock_camera, window_tracker=mock_window_tracker)

        # Stopped: active_app is None
        self.assertIsNone(sm.get_state()["active_app"])

        # Start session
        sm.start(planned_duration_sec=600)
        mock_window_tracker.start.assert_called_once()
        state = sm.get_state()
        self.assertEqual(
            state["active_app"],
            {"name": "Code.exe", "title": "main.py - VS Code"},
        )

        # Pause session
        sm.pause()
        mock_window_tracker.pause.assert_called_once()
        self.assertIsNone(sm.get_state()["active_app"])

        # Resume session
        sm.resume()
        mock_window_tracker.resume.assert_called_once()
        self.assertEqual(
            sm.get_state()["active_app"],
            {"name": "Code.exe", "title": "main.py - VS Code"},
        )

        # Stop session
        sm.stop()
        mock_window_tracker.stop.assert_called_once()
        self.assertIsNone(sm.get_state()["active_app"])


class TestWindowsWindowTrackerReal(unittest.TestCase):
    def test_windows_tracker_execution(self):
        if sys.platform != "win32":
            self.skipTest("Windows-only test")
        from app.tracking.windows import WindowsWindowTracker

        tracker = WindowsWindowTracker()
        win = tracker.get_active_window()
        # May be None if running non-interactively or in a background shell,
        # but if returned, must have 'name' and 'title' keys
        if win is not None:
            self.assertIn("name", win)
            self.assertIn("title", win)
            self.assertIsInstance(win["name"], str)
            self.assertIsInstance(win["title"], str)


if __name__ == "__main__":
    unittest.main()
