"""Tests for Phase 5: SQLite storage, interval recording, and session endpoints."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.session import SessionManager, SessionState
from app.storage.db import DatabaseManager
from app.storage.recorder import CameraActivityRecorder


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db = DatabaseManager(db_path=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_session_lifecycle_and_queries(self):
        # 1. Create session
        sid = self.db.create_session(start_time=100.0, planned_duration_sec=1800)
        self.assertIsInstance(sid, int)
        self.assertGreater(sid, 0)

        # 2. Finish session
        self.db.finish_session(session_id=sid, end_time=1900.0, paused_total_sec=60.0)

        # 3. Insert activity events
        activities = [
            {"activity_label": "sitting", "start_time": 100.0, "end_time": 1800.0},
            {"activity_label": "laptop", "start_time": 200.0, "end_time": 1500.0},
        ]
        self.db.insert_activity_events(sid, activities)

        # 4. Insert app events
        apps = [
            {"app_name": "Code.exe", "window_title": "app.py", "start_time": 100.0, "end_time": 1000.0},
            {"app_name": "chrome.exe", "window_title": "Docs", "start_time": 1000.0, "end_time": 1800.0},
        ]
        self.db.insert_app_events(sid, apps)

        # 5. Query session list
        sessions = self.db.get_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["id"], sid)
        self.assertEqual(sessions[0]["planned_duration_sec"], 1800)
        self.assertEqual(sessions[0]["paused_total_sec"], 60.0)

        # 6. Query session details
        details = self.db.get_session(sid)
        self.assertIsNotNone(details)
        self.assertEqual(details["id"], sid)
        self.assertEqual(len(details["activity_events"]), 2)
        self.assertEqual(details["activity_events"][0]["activity_label"], "sitting")
        self.assertEqual(len(details["app_events"]), 2)
        self.assertEqual(details["app_events"][0]["app_name"], "Code.exe")

    def test_nonexistent_session_returns_none(self):
        self.assertIsNone(self.db.get_session(99999))


class TestCameraActivityRecorder(unittest.TestCase):
    def setUp(self):
        self.recorder = CameraActivityRecorder()

    def test_overlapping_intervals_and_pause_isolation(self):
        # Start at t=10.0 with sitting
        self.recorder.start(initial_activities=["sitting"], now=10.0)

        # At t=12.0: laptop appears alongside sitting
        self.recorder.update(["sitting", "laptop"], now=12.0)

        # At t=15.0: laptop closed, only sitting remains
        self.recorder.update(["sitting"], now=15.0)

        # At t=18.0: session paused
        self.recorder.pause(now=18.0)

        # During pause (t=18.0 to t=25.0), open intervals should be completely empty
        events_during_pause = self.recorder.get_events()
        self.assertEqual(len(events_during_pause), 2)  # sitting (10-18) and laptop (12-15)

        # At t=25.0: session resumed with sitting + phone in hand
        self.recorder.resume(current_activities=["sitting", "phone in hand"], now=25.0)

        # At t=30.0: session stopped
        final_events = self.recorder.stop(now=30.0)

        # Verify all intervals
        # 1. sitting: 10.0 -> 18.0
        # 2. laptop: 12.0 -> 15.0
        # 3. sitting: 25.0 -> 30.0
        # 4. phone in hand: 25.0 -> 30.0
        self.assertEqual(len(final_events), 4)

        labels = [ev["activity_label"] for ev in final_events]
        self.assertEqual(labels.count("sitting"), 2)
        self.assertEqual(labels.count("laptop"), 1)
        self.assertEqual(labels.count("phone in hand"), 1)

        # Ensure paused period (18.0 to 25.0) was NOT recorded in any interval
        for ev in final_events:
            if ev["activity_label"] == "sitting":
                # Must be either before pause or after resume
                self.assertTrue(ev["end_time"] <= 18.0 or ev["start_time"] >= 25.0)


class TestSessionStorageIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db = DatabaseManager(db_path=self.temp_file.name)

        self.mock_camera = MagicMock()
        self.mock_camera.get_current_activities.return_value = ["sitting", "laptop"]

        self.mock_window_tracker = MagicMock()
        self.mock_window_tracker.get_intervals.return_value = [
            {"app_name": "Code.exe", "window_title": "study.py", "start_time": 100.0, "end_time": 110.0}
        ]
        self.mock_window_tracker.get_current_window.return_value = {
            "name": "Code.exe",
            "title": "study.py",
        }

        self.sm = SessionManager(
            camera=self.mock_camera,
            window_tracker=self.mock_window_tracker,
            db=self.db,
        )

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_full_session_persisted_to_db(self):
        # 1. Start session
        sid = self.sm.start(planned_duration_sec=600)
        self.assertIsNotNone(sid)
        self.assertEqual(self.sm.session_id, sid)

        # 2. Check WebSocket state payload has session_id
        state = self.sm.get_state()
        self.assertEqual(state["session_id"], sid)

        # 3. Stop session
        finished_id = self.sm.stop()
        self.assertEqual(finished_id, sid)
        self.assertIsNone(self.sm.session_id)

        # 4. Verify SQLite has recorded everything
        record = self.db.get_session(sid)
        self.assertIsNotNone(record)
        self.assertIsNotNone(record["end_time"])
        self.assertEqual(len(record["activity_events"]), 2)  # sitting and laptop
        self.assertEqual(len(record["app_events"]), 1)
        self.assertEqual(record["app_events"][0]["app_name"], "Code.exe")


class TestSessionRestEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_list_sessions_endpoint(self):
        response = self.client.get("/sessions")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_session_details_not_found(self):
        response = self.client.get("/sessions/99999999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
