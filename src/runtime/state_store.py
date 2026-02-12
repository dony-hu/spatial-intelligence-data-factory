import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Optional


class SQLiteStateStore:
    """Minimal sqlite-backed task state store."""

    def __init__(self, db_path: str = "database/agent_runtime.db"):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_state (
                    task_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert(self, task_id: str, state: str, payload: Dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO task_state(task_id, state, payload_json, updated_at)
                VALUES(?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(task_id) DO UPDATE SET
                  state=excluded.state,
                  payload_json=excluded.payload_json,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (task_id, state, json.dumps(payload, ensure_ascii=False)),
            )

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT task_id, state, payload_json, updated_at FROM task_state WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if not row:
                return None
            return {
                "task_id": row[0],
                "state": row[1],
                "payload": json.loads(row[2]),
                "updated_at": row[3],
            }
