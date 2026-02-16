import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class SQLiteEvidenceStore:
    """Evidence recorder (PostgreSQL-only)."""

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
                CREATE TABLE IF NOT EXISTS evidence_records (
                    id BIGSERIAL PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    artifact_ref TEXT NOT NULL,
                    result TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                )
                """
            )

    def append(
        self,
        task_id: str,
        actor: str,
        action: str,
        artifact_ref: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.cursor().execute(
                """
                INSERT INTO evidence_records(
                    task_id, timestamp, actor, action, artifact_ref, result, metadata_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    ts,
                    actor,
                    action,
                    artifact_ref,
                    result,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )

    def list_by_task(self, task_id: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.cursor().execute(
                """
                SELECT timestamp, actor, action, artifact_ref, result, metadata_json
                FROM evidence_records
                WHERE task_id=?
                ORDER BY id ASC
                """,
                (task_id,),
            ).fetchall()
        return [
            {
                "timestamp": r["timestamp"] if isinstance(r, dict) else r[0],
                "actor": r["actor"] if isinstance(r, dict) else r[1],
                "action": r["action"] if isinstance(r, dict) else r[2],
                "artifact_ref": r["artifact_ref"] if isinstance(r, dict) else r[3],
                "result": r["result"] if isinstance(r, dict) else r[4],
                "metadata": json.loads(r["metadata_json"] if isinstance(r, dict) else r[5]),
            }
            for r in rows
        ]


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

    def fetchall(self):
        return self._raw.fetchall()


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
