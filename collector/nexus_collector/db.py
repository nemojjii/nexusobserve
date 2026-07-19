"""SQLite persistence for Nexus decision records.

Records are stored as JSON blobs (the shape is owned by contracts/schema.py, so
the DB stays schema-agnostic beyond the indexed columns we query on).
"""

from __future__ import annotations

import os
import sqlite3
from typing import List, Optional

DB_PATH = os.environ.get("NEXUS_DB_PATH", "nexus.db")

# SQLite :memory: databases are per-connection — using a new connection each time
# produces separate empty databases. For in-memory mode, we keep one shared
# connection for the lifetime of the process.
_memory_conn: Optional[sqlite3.Connection] = None


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    global _memory_conn
    path = db_path or DB_PATH
    if path == ":memory:":
        if _memory_conn is None:
            _memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            _memory_conn.row_factory = sqlite3.Row
        return _memory_conn
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Create the decisions table if it does not exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                run_id      TEXT NOT NULL,
                timestamp   REAL NOT NULL,
                payload     TEXT NOT NULL        -- full DecisionRecord as JSON
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_decisions_run_id ON decisions(run_id)"
        )


def insert_decision(decision_id: str, run_id: str, timestamp: float,
                    payload_json: str, db_path: Optional[str] = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO decisions (decision_id, run_id, timestamp, payload) "
            "VALUES (?, ?, ?, ?)",
            (decision_id, run_id, timestamp, payload_json),
        )


def get_decisions_for_run(run_id: str, db_path: Optional[str] = None) -> List[str]:
    """Return the JSON payloads of all decisions for a run, oldest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT payload FROM decisions WHERE run_id = ? ORDER BY timestamp ASC",
            (run_id,),
        ).fetchall()
    return [row["payload"] for row in rows]


def get_decision_by_id(decision_id: str, db_path: Optional[str] = None) -> Optional[str]:
    """Return the JSON payload for a single decision, or None if not found."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT payload FROM decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    return row["payload"] if row else None


def list_run_ids(db_path: Optional[str] = None) -> List[str]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT run_id FROM decisions ORDER BY run_id"
        ).fetchall()
    return [row["run_id"] for row in rows]
