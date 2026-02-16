import json
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional


class SQLiteStateStore:
    """Task state store (PostgreSQL-only)."""

    def __init__(self, db_path: str = "database/agent_runtime.db"):
        self.database_url = str(os.getenv("DATABASE_URL") or "")
        if not self.database_url.startswith("postgresql"):
            raise RuntimeError("DATABASE_URL must be postgresql://... in PG-only mode")
        self._init_schema()

    @contextmanager
    def _conn(self):
        import psycopg2
        from psycopg2.extras import RealDictCursor

        raw_conn = psycopg2.connect(self.database_url)
        with raw_conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS control_plane")
            cur.execute("SET search_path TO control_plane, public")
        conn = _CompatConnection(raw_conn, cursor_factory=RealDictCursor)
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
            conn.cursor().execute(
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
            conn.cursor().execute(
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
            row = conn.cursor().execute(
                "SELECT task_id, state, payload_json, updated_at FROM task_state WHERE task_id=?",
                (task_id,),
            ).fetchone()
            if not row:
                return None
            if isinstance(row, dict):
                return {
                    "task_id": row["task_id"],
                    "state": row["state"],
                    "payload": json.loads(row["payload_json"]),
                    "updated_at": row["updated_at"],
                }
            return {
                "task_id": row[0],
                "state": row[1],
                "payload": json.loads(row[2]),
                "updated_at": row[3],
            }


class _CompatCursor:
    def __init__(self, raw_cursor: Any):
        self._raw = raw_cursor

    def execute(self, sql: str, params: Optional[tuple[Any, ...]] = None):
        if params is None:
            self._raw.execute(sql)
            return self
        sql = sql.replace("?", "%s")
        self._raw.execute(sql, params)
        return self

    def fetchone(self):
        return self._raw.fetchone()


class _CompatConnection:
    def __init__(self, raw_conn: Any, cursor_factory: Any = None):
        self._raw = raw_conn
        self._cursor_factory = cursor_factory

    def cursor(self):
        if self._cursor_factory is not None:
            return _CompatCursor(self._raw.cursor(cursor_factory=self._cursor_factory))
        return _CompatCursor(self._raw.cursor())

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()
