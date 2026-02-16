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
        # SQLiteEvidenceStore class and its methods have been removed.


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
