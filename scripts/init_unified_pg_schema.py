#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


def _apply_sql_file(conn, path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"sql file missing: {path}")
    sql_text = path.read_text(encoding="utf-8")
    conn.exec_driver_sql(sql_text)
    print(f"[OK] applied: {path.name}")


def _ensure_line_feedback_tables(conn) -> None:
    conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS address_line")
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.failure_queue (
            failure_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            status TEXT NOT NULL,
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.replay_runs (
            replay_id TEXT PRIMARY KEY,
            failure_id TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            status TEXT NOT NULL,
            result_json JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """
    )
    conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS idx_replay_runs_failure_id ON address_line.replay_runs(failure_id)"
    )
    print("[OK] ensured: address_line.failure_queue, address_line.replay_runs")


def _ensure_control_plane_schema(conn) -> None:
    conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS control_plane")
    print("[OK] ensured: control_plane schema")


def _ensure_address_line_merged_schema(conn) -> None:
    conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS address_line")

    # Governance core mapped into unified address_line schema (compatibility views).
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.batch AS
        SELECT * FROM public.addr_batch
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.raw_input AS
        SELECT
            raw_id AS input_id,
            batch_id,
            raw_text,
            province,
            city,
            district,
            street,
            detail,
            raw_hash,
            ingested_at AS created_at
        FROM public.addr_raw
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.standardized AS
        SELECT
            canonical_id AS standardized_id,
            raw_id AS input_id,
            canon_text AS standard_full_address,
            province AS standard_province,
            city AS standard_city,
            district AS standard_district,
            street AS standard_street,
            road,
            house_no,
            building,
            unit_no,
            room_no,
            confidence AS confidence_score,
            strategy,
            evidence,
            ruleset_version,
            trace_id,
            agent_run_id,
            created_at,
            updated_at
        FROM public.addr_canonical
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.review AS
        SELECT * FROM public.addr_review
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.ruleset AS
        SELECT * FROM public.addr_ruleset
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.change_request AS
        SELECT * FROM public.addr_change_request
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.task_run AS
        SELECT * FROM public.addr_task_run
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.audit_event AS
        SELECT * FROM public.addr_audit_event
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.api_audit_log AS
        SELECT * FROM public.api_audit_log
        """
    )
    conn.exec_driver_sql(
        """
        CREATE OR REPLACE VIEW address_line.agent_execution_log AS
        SELECT * FROM public.agent_execution_log
        """
    )

    # Supplementary entities from Address Graph Sample retained as native tables under address_line.
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.address_component (
            component_id TEXT PRIMARY KEY,
            component_type TEXT NOT NULL,
            name TEXT NOT NULL,
            parent_id TEXT,
            level INTEGER,
            region TEXT,
            standardized_name TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.address_standardization_rule (
            rule_id TEXT PRIMARY KEY,
            rule_type TEXT NOT NULL,
            source_pattern TEXT,
            target_pattern TEXT,
            region TEXT,
            priority INTEGER DEFAULT 100,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.address_entity_mapping (
            mapping_id TEXT PRIMARY KEY,
            standardized_id TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_name TEXT,
            similarity_score DOUBLE PRECISION,
            mapping_method TEXT,
            match_confidence DOUBLE PRECISION,
            source_db TEXT,
            region TEXT,
            is_confirmed BOOLEAN DEFAULT FALSE,
            confirmed_by TEXT,
            confirmed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.entity_multi_source_fusion (
            fusion_id TEXT PRIMARY KEY,
            canonical_entity_id TEXT NOT NULL,
            source_entity_id TEXT,
            source_db TEXT NOT NULL,
            fusion_score DOUBLE PRECISION,
            region TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.address_quality_metrics (
            metric_id TEXT PRIMARY KEY,
            batch_id TEXT,
            quality_score DOUBLE PRECISION,
            reviewed_count BIGINT DEFAULT 0,
            rejected_count BIGINT DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS address_line.address_library_version (
            version_id TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            version_tag TEXT NOT NULL,
            released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            notes TEXT
        )
        """
    )
    print("[OK] ensured: address_line merged schema")


def main() -> int:
    try:
        from sqlalchemy import create_engine
    except Exception:
        print("[ERROR] sqlalchemy is required. Install with: /Users/huda/Code/.venv/bin/python -m pip install sqlalchemy")
        return 2

    db_url = str(os.getenv("DATABASE_URL") or "")
    if not db_url.startswith("postgresql"):
        print("[ERROR] DATABASE_URL must be postgresql://...")
        return 2

    root = Path(__file__).resolve().parent.parent
    sql_files = [
        root / "database" / "postgres" / "sql" / "001_enable_extensions.sql",
        root / "database" / "postgres" / "sql" / "002_init_tables.sql",
        root / "database" / "postgres" / "sql" / "003_init_indexes.sql",
        root / "database" / "trust_meta_schema.sql",
    ]

    engine = create_engine(db_url)
    with engine.begin() as conn:
        for path in sql_files:
            try:
                _apply_sql_file(conn, path)
            except Exception as exc:
                print(f"[ERROR] failed applying {path.name}: {exc}")
                return 2
        try:
            _ensure_line_feedback_tables(conn)
        except Exception as exc:
            print(f"[ERROR] failed ensuring line feedback tables: {exc}")
            return 2
        try:
            _ensure_control_plane_schema(conn)
        except Exception as exc:
            print(f"[ERROR] failed ensuring control_plane schema: {exc}")
            return 2
        try:
            _ensure_address_line_merged_schema(conn)
        except Exception as exc:
            print(f"[ERROR] failed ensuring address_line merged schema: {exc}")
            return 2

    print("[DONE] unified pg schema initialized (governance + runtime control_plane + trust + address_line merged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
