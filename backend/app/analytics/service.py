"""Analytics aggregation service for study tracker data."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.storage.db import DatabaseManager


class AnalyticsService:
    """Calculates objective aggregations over recorded sessions and events."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get_summary(
        self,
        from_time: Optional[float] = None,
        to_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Aggregate total time, camera activity durations, and app usage."""
        with self.db.get_connection() as conn:
            # 1. Session totals
            query_sessions = """
                SELECT
                    id, start_time, end_time, paused_total_sec
                FROM sessions
                WHERE (:from_time IS NULL OR start_time >= :from_time)
                  AND (:to_time IS NULL OR start_time <= :to_time)
            """
            cur = conn.execute(query_sessions, {"from_time": from_time, "to_time": to_time})
            session_rows = cur.fetchall()

            session_count = len(session_rows)
            total_session_sec = 0.0
            total_paused_sec = 0.0

            session_ids = []
            for row in session_rows:
                session_ids.append(row["id"])
                end = row["end_time"] if row["end_time"] is not None else row["start_time"]
                paused = row["paused_total_sec"] or 0.0
                elapsed = max(0.0, end - row["start_time"] - paused)
                total_session_sec += elapsed
                total_paused_sec += paused

            # 2. Activity totals
            activities = []
            if session_ids:
                placeholders = ",".join("?" * len(session_ids))
                query_acts = f"""
                    SELECT
                        activity_label,
                        ROUND(SUM(MAX(0, end_time - start_time)), 1) AS duration_sec
                    FROM activity_events
                    WHERE session_id IN ({placeholders})
                    GROUP BY activity_label
                    ORDER BY duration_sec DESC
                """
                cur = conn.execute(query_acts, session_ids)
                for r in cur.fetchall():
                    activities.append({
                        "label": r["activity_label"],
                        "duration_sec": float(r["duration_sec"]),
                    })

            # 3. App totals
            apps = []
            if session_ids:
                placeholders = ",".join("?" * len(session_ids))
                query_apps = f"""
                    SELECT
                        app_name,
                        ROUND(SUM(MAX(0, end_time - start_time)), 1) AS duration_sec
                    FROM app_events
                    WHERE session_id IN ({placeholders})
                    GROUP BY app_name
                    ORDER BY duration_sec DESC
                """
                cur = conn.execute(query_apps, session_ids)
                for r in cur.fetchall():
                    apps.append({
                        "app_name": r["app_name"],
                        "duration_sec": float(r["duration_sec"]),
                    })

            return {
                "session_count": session_count,
                "total_session_sec": round(total_session_sec, 1),
                "total_paused_sec": round(total_paused_sec, 1),
                "activities": activities,
                "apps": apps,
            }

    def get_daily(self, limit_days: int = 30) -> List[Dict[str, Any]]:
        """Aggregate daily session time and activity breakdowns."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, start_time, end_time, paused_total_sec
                FROM sessions
                ORDER BY start_time ASC
                """
            )
            rows = cur.fetchall()

            daily_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "date": "",
                "session_count": 0,
                "total_session_sec": 0.0,
                "total_paused_sec": 0.0,
                "session_ids": [],
            })

            for row in rows:
                dt = datetime.fromtimestamp(row["start_time"])
                date_str = dt.strftime("%Y-%m-%d")

                end = row["end_time"] if row["end_time"] is not None else row["start_time"]
                paused = row["paused_total_sec"] or 0.0
                elapsed = max(0.0, end - row["start_time"] - paused)

                daily_map[date_str]["date"] = date_str
                daily_map[date_str]["session_count"] += 1
                daily_map[date_str]["total_session_sec"] += elapsed
                daily_map[date_str]["total_paused_sec"] += paused
                daily_map[date_str]["session_ids"].append(row["id"])

            # Sort by date descending and limit
            sorted_dates = sorted(daily_map.keys(), reverse=True)[:limit_days]
            result = []

            for date_str in reversed(sorted_dates):
                item = daily_map[date_str]
                s_ids = item["session_ids"]

                activities_dict = defaultdict(float)
                if s_ids:
                    placeholders = ",".join("?" * len(s_ids))
                    q = f"""
                        SELECT activity_label, SUM(MAX(0, end_time - start_time)) AS dur
                        FROM activity_events
                        WHERE session_id IN ({placeholders})
                        GROUP BY activity_label
                    """
                    for r in conn.execute(q, s_ids).fetchall():
                        activities_dict[r["activity_label"]] = round(float(r["dur"]), 1)

                result.append({
                    "date": item["date"],
                    "session_count": item["session_count"],
                    "total_session_sec": round(item["total_session_sec"], 1),
                    "total_paused_sec": round(item["total_paused_sec"], 1),
                    "activities": dict(activities_dict),
                })

            return result

    def get_weekly(self, limit_weeks: int = 12) -> List[Dict[str, Any]]:
        """Aggregate weekly session time and activity breakdowns."""
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, start_time, end_time, paused_total_sec
                FROM sessions
                ORDER BY start_time ASC
                """
            )
            rows = cur.fetchall()

            weekly_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "week": "",
                "session_count": 0,
                "total_session_sec": 0.0,
                "total_paused_sec": 0.0,
                "session_ids": [],
            })

            for row in rows:
                dt = datetime.fromtimestamp(row["start_time"])
                # ISO year and week
                year, week_num, _ = dt.isocalendar()
                week_str = f"{year}-W{week_num:02d}"

                end = row["end_time"] if row["end_time"] is not None else row["start_time"]
                paused = row["paused_total_sec"] or 0.0
                elapsed = max(0.0, end - row["start_time"] - paused)

                weekly_map[week_str]["week"] = week_str
                weekly_map[week_str]["session_count"] += 1
                weekly_map[week_str]["total_session_sec"] += elapsed
                weekly_map[week_str]["total_paused_sec"] += paused
                weekly_map[week_str]["session_ids"].append(row["id"])

            sorted_weeks = sorted(weekly_map.keys(), reverse=True)[:limit_weeks]
            result = []

            for week_str in reversed(sorted_weeks):
                item = weekly_map[week_str]
                result.append({
                    "week": item["week"],
                    "session_count": item["session_count"],
                    "total_session_sec": round(item["total_session_sec"], 1),
                    "total_paused_sec": round(item["total_paused_sec"], 1),
                })

            return result
