import json
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional


class PGStateStore:
    """Task runtime state store backed by PostgreSQL."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = str(database_url or os.getenv("DATABASE_URL") or "")
        if not self.database_url.startswith("postgresql"):
            raise RuntimeError("DATABASE_URL must be postgresql://... in PG-only mode")
        self._init_schema()

    @contextmanager
    def _conn(self):
        driver_dsn = self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            conn = psycopg2.connect(driver_dsn)
            cursor_factory = RealDictCursor
        except Exception:
            import psycopg

            conn = psycopg.connect(driver_dsn)
            cursor_factory = None

        compat = _CompatConnection(conn, cursor_factory=cursor_factory)
        try:
            yield compat
            compat.commit()
        except Exception:
            compat.rollback()
            raise
        finally:
            compat.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("CREATE SCHEMA IF NOT EXISTS control_plane")
            cur.execute("SET search_path TO control_plane, public")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_state (
                    task_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

    def upsert(self, task_id: str, state: str, payload: Dict[str, Any]) -> None:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SET search_path TO control_plane, public")
            cur.execute(
                """
                INSERT INTO task_state(task_id, state, payload_json, updated_at)
                VALUES(%s, %s, %s, NOW())
                ON CONFLICT(task_id) DO UPDATE SET
                  state=EXCLUDED.state,
                  payload_json=EXCLUDED.payload_json,
                  updated_at=NOW()
                """,
                (task_id, state, json.dumps(payload, ensure_ascii=False)),
            )

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SET search_path TO control_plane, public")
            row = cur.execute(
                "SELECT task_id, state, payload_json, updated_at FROM task_state WHERE task_id=%s",
                (task_id,),
            ).fetchone()
            if not row:
                return None
            if isinstance(row, dict):
                return {
                    "task_id": row["task_id"],
                    "state": row["state"],
                    "payload": json.loads(row["payload_json"]),
                    "updated_at": str(row["updated_at"]),
                }
            return {
                "task_id": row[0],
                "state": row[1],
                "payload": json.loads(row[2]),
                "updated_at": str(row[3]),
            }


class _CompatCursor:
    def __init__(self, raw_cursor: Any):
        self._raw = raw_cursor

    def execute(self, sql: str, params: Optional[tuple[Any, ...]] = None):
        if params is None:
            self._raw.execute(sql)
            return self
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
