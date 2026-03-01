import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class PGEvidenceStore:
    """Evidence recorder backed by PostgreSQL."""

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
                CREATE TABLE IF NOT EXISTS evidence_records (
                    id BIGSERIAL PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    ts TIMESTAMPTZ NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    artifact_ref TEXT NOT NULL,
                    result TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_evidence_task_ts ON evidence_records(task_id, ts)")

    def append(
        self,
        task_id: str,
        actor: str,
        action: str,
        artifact_ref: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = metadata or {}
        ts = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SET search_path TO control_plane, public")
            cur.execute(
                """
                INSERT INTO evidence_records(task_id, ts, actor, action, artifact_ref, result, metadata_json)
                VALUES(%s, %s, %s, %s, %s, %s, %s)
                """,
                (task_id, ts, actor, action, artifact_ref, result, json.dumps(payload, ensure_ascii=False)),
            )

    def list_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SET search_path TO control_plane, public")
            rows = cur.execute(
                """
                SELECT task_id, ts, actor, action, artifact_ref, result, metadata_json
                FROM evidence_records
                WHERE task_id=%s
                ORDER BY ts ASC
                """,
                (task_id,),
            ).fetchall()

            output: List[Dict[str, Any]] = []
            for row in rows:
                if isinstance(row, dict):
                    output.append(
                        {
                            "task_id": row["task_id"],
                            "ts": str(row["ts"]),
                            "actor": row["actor"],
                            "action": row["action"],
                            "artifact_ref": row["artifact_ref"],
                            "result": row["result"],
                            "metadata": json.loads(row["metadata_json"]),
                        }
                    )
                    continue
                output.append(
                    {
                        "task_id": row[0],
                        "ts": str(row[1]),
                        "actor": row[2],
                        "action": row[3],
                        "artifact_ref": row[4],
                        "result": row[5],
                        "metadata": json.loads(row[6]),
                    }
                )
            return output


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
