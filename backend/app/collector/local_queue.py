"""
Local SQLite fallback queue (SDD FR-1.3 / Section 14.2).
Buffers telemetry readings if the API is unreachable and replays them,
in order, once connectivity returns.
"""
import json
import sqlite3
from contextlib import closing


class LocalQueue:
    def __init__(self, db_path: str = "./collector_queue.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def enqueue(self, payload: dict):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO queue (payload, created_at) VALUES (?, ?)",
                (json.dumps(payload), payload.get("timestamp", "")),
            )
            conn.commit()

    def peek_batch(self, limit: int = 50):
        with closing(sqlite3.connect(self.db_path)) as conn:
            cur = conn.execute(
                "SELECT id, payload FROM queue ORDER BY id ASC LIMIT ?", (limit,)
            )
            return [(row[0], json.loads(row[1])) for row in cur.fetchall()]

    def remove(self, row_id: int):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("DELETE FROM queue WHERE id = ?", (row_id,))
            conn.commit()

    def size(self) -> int:
        with closing(sqlite3.connect(self.db_path)) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM queue")
            return cur.fetchone()[0]
