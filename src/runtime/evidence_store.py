import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class SQLiteEvidenceStore:
    """Minimal sqlite-backed evidence recorder."""

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
                CREATE TABLE IF NOT EXISTS evidence_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            conn.execute(
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
            rows = conn.execute(
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
                "timestamp": r[0],
                "actor": r[1],
                "action": r[2],
                "artifact_ref": r[3],
                "result": r[4],
                "metadata": json.loads(r[5]),
            }
            for r in rows
        ]
