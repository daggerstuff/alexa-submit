from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any


class SessionStore:
    """SQLite-backed session persistence with a process-local lock.

    Rows store opaque JSON text; the orchestrator owns pydantic/dataclass
    (de)serialization and passes plain ``dict`` records in and out. The store
    survives process restarts within a container. To survive App Runner
    redeploys, point ``SESSION_DB_PATH`` at a mounted EFS volume (or swap this
    class for a DynamoDB-backed store when scaling past one instance).
    """

    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                patient_state TEXT NOT NULL,
                transcript TEXT NOT NULL,
                processed_events TEXT NOT NULL,
                status TEXT NOT NULL,
                last_accessed REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def upsert(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO sessions
                    (session_id, scenario_id, patient_state, transcript, processed_events, status, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    scenario_id = excluded.scenario_id,
                    patient_state = excluded.patient_state,
                    transcript = excluded.transcript,
                    processed_events = excluded.processed_events,
                    status = excluded.status,
                    last_accessed = excluded.last_accessed
                """,
                (
                    record["session_id"],
                    record["scenario_id"],
                    json.dumps(record["patient_state"]),
                    json.dumps(record["transcript"]),
                    json.dumps(record["processed_events"]),
                    record["status"],
                    record["last_accessed"],
                ),
            )
            self._conn.commit()

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT scenario_id, patient_state, transcript, processed_events, status, last_accessed
                FROM sessions WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "session_id": session_id,
            "scenario_id": row[0],
            "patient_state": json.loads(row[1]),
            "transcript": json.loads(row[2]),
            "processed_events": json.loads(row[3]),
            "status": row[4],
            "last_accessed": row[5],
        }

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            self._conn.commit()

    def delete_expired(self, cutoff: float) -> int:
        """Delete rows whose ``last_accessed`` predates ``cutoff``; return the count."""
        with self._lock:
            cursor = self._conn.execute("DELETE FROM sessions WHERE last_accessed < ?", (cutoff,))
            self._conn.commit()
            return cursor.rowcount

    def close(self) -> None:
        with self._lock:
            self._conn.close()
