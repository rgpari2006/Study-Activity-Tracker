"""SQLite database connection and schema management."""

import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from app.config import DB_PATH


class DatabaseManager:
    """Manages SQLite storage for study sessions, activity intervals, and app events."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        """Create tables if they do not exist."""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    planned_duration_sec INTEGER NOT NULL,
                    paused_total_sec REAL DEFAULT 0.0
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    activity_label TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    app_name TEXT NOT NULL,
                    window_title TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                );
            """)

    def create_session(self, start_time: float, planned_duration_sec: int) -> int:
        """Insert a new session row and return the generated ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (start_time, planned_duration_sec, paused_total_sec)
                VALUES (?, ?, 0.0)
                """,
                (start_time, planned_duration_sec),
            )
            return cursor.lastrowid

    def finish_session(
        self,
        session_id: int,
        end_time: float,
        paused_total_sec: float,
    ) -> None:
        """Update a session record when stopped."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET end_time = ?, paused_total_sec = ?
                WHERE id = ?
                """,
                (end_time, paused_total_sec, session_id),
            )

    def insert_activity_events(
        self,
        session_id: int,
        events: List[Dict[str, Any]],
    ) -> None:
        """Batch insert activity intervals for a session."""
        if not events:
            return
        rows = [
            (session_id, ev["activity_label"], ev["start_time"], ev["end_time"])
            for ev in events
        ]
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO activity_events (session_id, activity_label, start_time, end_time)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )

    def insert_app_events(
        self,
        session_id: int,
        events: List[Dict[str, Any]],
    ) -> None:
        """Batch insert app intervals for a session."""
        if not events:
            return
        rows = [
            (session_id, ev["app_name"], ev["window_title"], ev["start_time"], ev["end_time"])
            for ev in events
        ]
        with self.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO app_events (session_id, app_name, window_title, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

    def get_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions ordered by id descending."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, start_time, end_time, planned_duration_sec, paused_total_sec
                FROM sessions
                ORDER BY id DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a single session with all associated activity and app events."""
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, start_time, end_time, planned_duration_sec, paused_total_sec
                FROM sessions
                WHERE id = ?
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            session = dict(row)

            # Fetch activity events
            act_cur = conn.execute(
                """
                SELECT id, session_id, activity_label, start_time, end_time
                FROM activity_events
                WHERE session_id = ?
                ORDER BY start_time ASC
                """,
                (session_id,),
            )
            session["activity_events"] = [dict(r) for r in act_cur.fetchall()]

            # Fetch app events
            app_cur = conn.execute(
                """
                SELECT id, session_id, app_name, window_title, start_time, end_time
                FROM app_events
                WHERE session_id = ?
                ORDER BY start_time ASC
                """,
                (session_id,),
            )
            session["app_events"] = [dict(r) for r in app_cur.fetchall()]

            return session
