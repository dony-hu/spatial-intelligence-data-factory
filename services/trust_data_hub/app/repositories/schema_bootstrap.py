from __future__ import annotations

import threading
from pathlib import Path

_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAPPED_DSN: set[str] = set()


def _split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []
    if current:
        statements.append("\n".join(current))
    return statements


def _reconcile_trust_meta_legacy(engine) -> None:
    # Legacy DB may have trust_meta.validation_replay_run without created_at.
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.validation_replay_run
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.validation_replay_run
            ADD COLUMN IF NOT EXISTS snapshot_id TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS source_id TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS version_tag TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS etag TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS last_modified TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS content_hash TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS raw_uri TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS parsed_uri TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS parsed_payload JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS status TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.source_snapshot
            ADD COLUMN IF NOT EXISTS row_count BIGINT NOT NULL DEFAULT 0
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.active_release
            ADD COLUMN IF NOT EXISTS source_id TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.active_release
            ADD COLUMN IF NOT EXISTS activated_by TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.active_release
            ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.active_release
            ADD COLUMN IF NOT EXISTS activation_note TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.snapshot_quality_report
            ADD COLUMN IF NOT EXISTS report_json JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.snapshot_quality_report
            ADD COLUMN IF NOT EXISTS quality_score INTEGER
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.snapshot_quality_report
            ADD COLUMN IF NOT EXISTS validator_version TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.snapshot_diff_report
            ADD COLUMN IF NOT EXISTS diff_json JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.snapshot_diff_report
            ADD COLUMN IF NOT EXISTS diff_severity TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.validation_replay_run
            ADD COLUMN IF NOT EXISTS replay_id TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.validation_replay_run
            ADD COLUMN IF NOT EXISTS request_payload JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.validation_replay_run
            ADD COLUMN IF NOT EXISTS replay_result JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_meta.validation_replay_run
            ADD COLUMN IF NOT EXISTS schema_version TEXT
            """
        )
        conn.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_validation_replay_ns_created
            ON trust_meta.validation_replay_run(namespace_id, created_at DESC)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_validation_replay_ns_snapshot
            ON trust_meta.validation_replay_run(namespace_id, snapshot_id)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_source_snapshot_ns_snapshot
            ON trust_meta.source_snapshot(namespace_id, snapshot_id)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_active_release_ns_source
            ON trust_meta.active_release(namespace_id, source_id)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_quality_ns_snapshot
            ON trust_meta.snapshot_quality_report(namespace_id, snapshot_id)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_diff_ns_new_snapshot
            ON trust_meta.snapshot_diff_report(namespace_id, new_snapshot_id)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_replay_id
            ON trust_meta.validation_replay_run(replay_id)
            """
        )
        # Trust DB tables in older local DBs may miss normalized/metadata columns.
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.admin_division
            ADD COLUMN IF NOT EXISTS parent_adcode TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.admin_division
            ADD COLUMN IF NOT EXISTS division_id TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.admin_division
            ADD COLUMN IF NOT EXISTS parent_id TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.admin_division
            ADD COLUMN IF NOT EXISTS name_aliases JSONB NOT NULL DEFAULT '[]'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.admin_division
            ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.admin_division
            ADD COLUMN IF NOT EXISTS valid_to TIMESTAMPTZ
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.road_index
            ADD COLUMN IF NOT EXISTS normalized_name TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.road_index
            ADD COLUMN IF NOT EXISTS geometry_ref TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.road_index
            ADD COLUMN IF NOT EXISTS alias_names JSONB NOT NULL DEFAULT '[]'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.road_index
            ADD COLUMN IF NOT EXISTS adcode TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.road_index
            ADD COLUMN IF NOT EXISTS admin_adcode TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.poi_index
            ADD COLUMN IF NOT EXISTS normalized_name TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.poi_index
            ADD COLUMN IF NOT EXISTS category TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.poi_index
            ADD COLUMN IF NOT EXISTS centroid TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.poi_index
            ADD COLUMN IF NOT EXISTS adcode TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.poi_index
            ADD COLUMN IF NOT EXISTS admin_adcode TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.poi_index
            ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.poi_index
            ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS normalized_name TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS type TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS admin_adcode TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS centroid TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS confidence_hint DOUBLE PRECISION
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS alias_names JSONB NOT NULL DEFAULT '[]'::jsonb
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS category TEXT
            """
        )
        conn.exec_driver_sql(
            """
            ALTER TABLE IF EXISTS trust_db.place_name_index
            ADD COLUMN IF NOT EXISTS adcode TEXT
            """
        )
        conn.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_admin_division_ns_name
            ON trust_db.admin_division(namespace_id, name)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_road_index_ns_name
            ON trust_db.road_index(namespace_id, normalized_name)
            """
        )
        conn.exec_driver_sql(
            """
            CREATE INDEX IF NOT EXISTS idx_poi_index_ns_name
            ON trust_db.poi_index(namespace_id, normalized_name)
            """
        )


def ensure_trust_pg_schema(dsn: str | None) -> None:
    """Ensure trust_meta/trust_db schemas exist for a given PostgreSQL DSN."""
    if not dsn or not str(dsn).startswith("postgresql"):
        return

    normalized = str(dsn).strip()
    with _BOOTSTRAP_LOCK:
        if normalized in _BOOTSTRAPPED_DSN:
            return

        from sqlalchemy import create_engine

        root = Path(__file__).resolve().parents[4]
        sql_path = root / "database" / "trust_meta_schema.sql"
        engine = create_engine(normalized, future=True)
        sql_text = sql_path.read_text(encoding="utf-8")
        for stmt in _split_sql_statements(sql_text):
            try:
                with engine.begin() as conn:
                    conn.exec_driver_sql(stmt)
            except Exception as exc:
                message = str(exc)
                # Compatible with legacy schema where created_at may be absent.
                if "created_at" in message and "validation_replay" in message:
                    continue
                if "does not exist" in message and "CREATE INDEX IF NOT EXISTS idx_" in stmt:
                    continue
                raise

        _reconcile_trust_meta_legacy(engine)

        _BOOTSTRAPPED_DSN.add(normalized)
