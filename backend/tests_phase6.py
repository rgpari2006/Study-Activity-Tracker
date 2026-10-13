"""Tests for Phase 6: Analytics queries, aggregation, and REST endpoints."""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.analytics.service import AnalyticsService
from app.main import app
from app.storage.db import DatabaseManager


class TestAnalyticsService(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_file.close()
        self.db = DatabaseManager(db_path=self.temp_file.name)
        self.service = AnalyticsService(self.db)

        # Seed test data:
        # Session 1: start=1000.0, end=2000.0 (1000s), paused=100.0 (net 900s)
        s1 = self.db.create_session(start_time=1000.0, planned_duration_sec=1500)
        self.db.finish_session(session_id=s1, end_time=2000.0, paused_total_sec=100.0)
        self.db.insert_activity_events(s1, [
            {"activity_label": "sitting", "start_time": 1000.0, "end_time": 1900.0},  # 900s
            {"activity_label": "laptop", "start_time": 1100.0, "end_time": 1700.0},   # 600s
        ])
        self.db.insert_app_events(s1, [
            {"app_name": "Code.exe", "window_title": "main.py", "start_time": 1000.0, "end_time": 1900.0},  # 900s
        ])

        # Session 2: start=5000.0, end=7000.0 (2000s), paused=0.0 (net 2000s)
        s2 = self.db.create_session(start_time=5000.0, planned_duration_sec=3000)
        self.db.finish_session(session_id=s2, end_time=7000.0, paused_total_sec=0.0)
        self.db.insert_activity_events(s2, [
            {"activity_label": "sitting", "start_time": 5000.0, "end_time": 7000.0},     # 2000s
            {"activity_label": "book/paper", "start_time": 5500.0, "end_time": 6500.0},  # 1000s
        ])
        self.db.insert_app_events(s2, [
            {"app_name": "chrome.exe", "window_title": "Paper PDF", "start_time": 5000.0, "end_time": 6500.0},  # 1500s
        ])

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_summary_all_time(self):
        summary = self.service.get_summary()
        self.assertEqual(summary["session_count"], 2)
        self.assertEqual(summary["total_session_sec"], 2900.0)
        self.assertEqual(summary["total_paused_sec"], 100.0)

        # Activities check
        acts = {a["label"]: a["duration_sec"] for a in summary["activities"]}
        self.assertEqual(acts["sitting"], 2900.0)
        self.assertEqual(acts["laptop"], 600.0)
        self.assertEqual(acts["book/paper"], 1000.0)

        # Apps check
        apps = {ap["app_name"]: ap["duration_sec"] for ap in summary["apps"]}
        self.assertEqual(apps["Code.exe"], 900.0)
        self.assertEqual(apps["chrome.exe"], 1500.0)

    def test_summary_with_time_range(self):
        # Filter only Session 1 (start 1000.0 <= 3000.0)
        summary = self.service.get_summary(from_time=500.0, to_time=3000.0)
        self.assertEqual(summary["session_count"], 1)
        self.assertEqual(summary["total_session_sec"], 900.0)

        acts = {a["label"]: a["duration_sec"] for a in summary["activities"]}
        self.assertIn("laptop", acts)
        self.assertNotIn("book/paper", acts)

    def test_daily_and_weekly_history(self):
        daily = self.service.get_daily()
        self.assertGreaterEqual(len(daily), 1)
        first_day = daily[0]
        self.assertIn("date", first_day)
        self.assertIn("total_session_sec", first_day)
        self.assertIn("activities", first_day)

        weekly = self.service.get_weekly()
        self.assertGreaterEqual(len(weekly), 1)
        first_week = weekly[0]
        self.assertIn("week", first_week)
        self.assertIn("total_session_sec", first_week)


class TestAnalyticsRestEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_summary_endpoint(self):
        res = self.client.get("/analytics/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("session_count", data)
        self.assertIn("total_session_sec", data)
        self.assertIn("activities", data)
        self.assertIn("apps", data)

    def test_daily_endpoint(self):
        res = self.client.get("/analytics/daily")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_weekly_endpoint(self):
        res = self.client.get("/analytics/weekly")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)


if __name__ == "__main__":
    unittest.main()
