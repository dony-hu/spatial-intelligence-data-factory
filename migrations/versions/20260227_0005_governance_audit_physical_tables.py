"""governance and audit physical tables

Revision ID: 20260227_0005
Revises: 20260227_0004
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op


revision = "20260227_0005"
down_revision = "20260227_0004"
branch_labels = None
depends_on = None


def _drop_view_if_exists(schema: str, name: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = '{schema}' AND c.relname = '{name}' AND c.relkind IN ('v', 'm')
          ) THEN
            EXECUTE 'DROP VIEW {schema}.{name}';
          END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS governance;")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit;")

    _drop_view_if_exists("governance", "batch")
    _drop_view_if_exists("governance", "task_run")
    _drop_view_if_exists("governance", "raw_record")
    _drop_view_if_exists("governance", "canonical_record")
    _drop_view_if_exists("governance", "review")
    _drop_view_if_exists("governance", "ruleset")
    _drop_view_if_exists("governance", "change_request")
    _drop_view_if_exists("governance", "observation_event")
    _drop_view_if_exists("governance", "observation_metric")
    _drop_view_if_exists("governance", "alert_event")
    _drop_view_if_exists("audit", "event_log")
    _drop_view_if_exists("audit", "api_audit_log")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.batch (
            batch_id VARCHAR(64) PRIMARY KEY,
            batch_name VARCHAR(255) NOT NULL,
            source VARCHAR(128),
            status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.task_run (
            task_id VARCHAR(64) PRIMARY KEY,
            batch_id VARCHAR(64),
            status VARCHAR(32) NOT NULL,
            retry_count INT NOT NULL DEFAULT 0,
            error_code VARCHAR(64),
            error_message TEXT,
            trace_id VARCHAR(64),
            agent_run_id VARCHAR(64),
            runtime VARCHAR(32),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMPTZ
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.raw_record (
            raw_id VARCHAR(64) PRIMARY KEY,
            batch_id VARCHAR(64) NOT NULL,
            raw_text TEXT NOT NULL,
            province VARCHAR(64),
            city VARCHAR(64),
            district VARCHAR(64),
            street VARCHAR(128),
            detail TEXT,
            raw_hash VARCHAR(128) NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.canonical_record (
            canonical_id VARCHAR(64) PRIMARY KEY,
            raw_id VARCHAR(64) NOT NULL,
            canon_text TEXT NOT NULL,
            province VARCHAR(64),
            city VARCHAR(64),
            district VARCHAR(64),
            street VARCHAR(128),
            road VARCHAR(128),
            house_no VARCHAR(64),
            building VARCHAR(64),
            unit_no VARCHAR(64),
            room_no VARCHAR(64),
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
            strategy VARCHAR(64) NOT NULL,
            evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
            ruleset_version VARCHAR(64),
            trace_id VARCHAR(64),
            agent_run_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.review (
            review_id VARCHAR(64) PRIMARY KEY,
            raw_id VARCHAR(64) NOT NULL,
            review_status VARCHAR(32) NOT NULL,
            final_canon_text TEXT,
            reviewer VARCHAR(128),
            comment TEXT,
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.ruleset (
            ruleset_id VARCHAR(64) PRIMARY KEY,
            version VARCHAR(64) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT FALSE,
            config_json JSONB NOT NULL,
            created_by VARCHAR(128),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.change_request (
            change_id VARCHAR(64) PRIMARY KEY,
            from_ruleset_id VARCHAR(64) NOT NULL,
            to_ruleset_id VARCHAR(64) NOT NULL,
            baseline_task_id VARCHAR(64) NOT NULL,
            candidate_task_id VARCHAR(64) NOT NULL,
            diff_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            scorecard_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            recommendation VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            approved_by VARCHAR(128),
            approved_at TIMESTAMPTZ,
            review_comment TEXT,
            evidence_bullets JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.observation_event (
            event_id VARCHAR(64) PRIMARY KEY,
            trace_id VARCHAR(128) NOT NULL,
            span_id VARCHAR(128),
            source_service VARCHAR(64) NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            severity VARCHAR(16) NOT NULL,
            task_id VARCHAR(64),
            workpackage_id VARCHAR(128),
            ruleset_id VARCHAR(64),
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.observation_metric (
            metric_id VARCHAR(64) PRIMARY KEY,
            metric_name VARCHAR(128) NOT NULL,
            metric_value DOUBLE PRECISION NOT NULL,
            labels_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            window_start TIMESTAMPTZ,
            window_end TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS governance.alert_event (
            alert_id VARCHAR(64) PRIMARY KEY,
            alert_rule VARCHAR(128) NOT NULL,
            severity VARCHAR(16) NOT NULL,
            status VARCHAR(32) NOT NULL,
            trigger_value DOUBLE PRECISION NOT NULL,
            threshold_value DOUBLE PRECISION NOT NULL,
            trace_id VARCHAR(128),
            task_id VARCHAR(64),
            workpackage_id VARCHAR(128),
            owner VARCHAR(128),
            ack_by VARCHAR(128),
            ack_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.event_log (
            event_id VARCHAR(64) PRIMARY KEY,
            event_type VARCHAR(64) NOT NULL,
            caller VARCHAR(128) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            related_change_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.api_audit_log (
            audit_id VARCHAR(64) PRIMARY KEY,
            route VARCHAR(255) NOT NULL,
            method VARCHAR(16) NOT NULL,
            status_code INT,
            trace_id VARCHAR(64),
            task_id VARCHAR(64),
            actor VARCHAR(128),
            message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute(
        """
        INSERT INTO governance.batch (batch_id, batch_name, source, status, created_at, updated_at)
        SELECT batch_id, batch_name, source, status, created_at, updated_at
        FROM public.addr_batch
        ON CONFLICT (batch_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.task_run (
            task_id, batch_id, status, retry_count, error_code, error_message, trace_id, agent_run_id, runtime, created_at, updated_at, finished_at
        )
        SELECT task_id, batch_id, status, retry_count, error_code, error_message, trace_id, agent_run_id, runtime, created_at, updated_at, finished_at
        FROM public.addr_task_run
        ON CONFLICT (task_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.raw_record (
            raw_id, batch_id, raw_text, province, city, district, street, detail, raw_hash, ingested_at
        )
        SELECT raw_id, batch_id, raw_text, province, city, district, street, detail, raw_hash, ingested_at
        FROM public.addr_raw
        ON CONFLICT (raw_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.canonical_record (
            canonical_id, raw_id, canon_text, province, city, district, street, road, house_no, building, unit_no, room_no,
            confidence, strategy, evidence, ruleset_version, trace_id, agent_run_id, created_at, updated_at
        )
        SELECT canonical_id, raw_id, canon_text, province, city, district, street, road, house_no, building, unit_no, room_no,
               confidence, strategy, evidence, ruleset_version, trace_id, agent_run_id, created_at, updated_at
        FROM public.addr_canonical
        ON CONFLICT (canonical_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.review (
            review_id, raw_id, review_status, final_canon_text, reviewer, comment, reviewed_at, created_at, updated_at
        )
        SELECT review_id, raw_id, review_status, final_canon_text, reviewer, comment, reviewed_at, created_at, updated_at
        FROM public.addr_review
        ON CONFLICT (review_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.ruleset (ruleset_id, version, is_active, config_json, created_by, created_at, updated_at)
        SELECT ruleset_id, version, is_active, config_json, created_by, created_at, updated_at
        FROM public.addr_ruleset
        ON CONFLICT (ruleset_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.change_request (
            change_id, from_ruleset_id, to_ruleset_id, baseline_task_id, candidate_task_id, diff_json, scorecard_json,
            recommendation, status, approved_by, approved_at, review_comment, evidence_bullets, created_at, updated_at
        )
        SELECT change_id, from_ruleset_id, to_ruleset_id, baseline_task_id, candidate_task_id, diff_json, scorecard_json,
               recommendation, status, approved_by, approved_at, review_comment, evidence_bullets, created_at, updated_at
        FROM public.addr_change_request
        ON CONFLICT (change_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.observation_event (
            event_id, trace_id, span_id, source_service, event_type, status, severity, task_id, workpackage_id, ruleset_id, payload_json, created_at
        )
        SELECT event_id, trace_id, span_id, source_service, event_type, status, severity, task_id, workpackage_id, ruleset_id, payload_json, created_at
        FROM public.addr_observation_event
        ON CONFLICT (event_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.observation_metric (metric_id, metric_name, metric_value, labels_json, window_start, window_end, created_at)
        SELECT metric_id, metric_name, metric_value, labels_json, window_start, window_end, created_at
        FROM public.addr_observation_metric
        ON CONFLICT (metric_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO governance.alert_event (
            alert_id, alert_rule, severity, status, trigger_value, threshold_value, trace_id, task_id, workpackage_id,
            owner, ack_by, ack_at, created_at, updated_at
        )
        SELECT alert_id, alert_rule, severity, status, trigger_value, threshold_value, trace_id, task_id, workpackage_id,
               owner, ack_by, ack_at, created_at, updated_at
        FROM public.addr_alert_event
        ON CONFLICT (alert_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO audit.event_log (event_id, event_type, caller, payload, related_change_id, created_at)
        SELECT event_id, event_type, caller, payload, related_change_id, created_at
        FROM public.addr_audit_event
        ON CONFLICT (event_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO audit.api_audit_log (
            audit_id, route, method, status_code, trace_id, task_id, actor, message, created_at
        )
        SELECT audit_id, route, method, status_code, trace_id, task_id, actor, message, created_at
        FROM public.api_audit_log
        ON CONFLICT (audit_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit.api_audit_log;")
    op.execute("DROP TABLE IF EXISTS audit.event_log;")
    op.execute("DROP TABLE IF EXISTS governance.alert_event;")
    op.execute("DROP TABLE IF EXISTS governance.observation_metric;")
    op.execute("DROP TABLE IF EXISTS governance.observation_event;")
    op.execute("DROP TABLE IF EXISTS governance.change_request;")
    op.execute("DROP TABLE IF EXISTS governance.ruleset;")
    op.execute("DROP TABLE IF EXISTS governance.review;")
    op.execute("DROP TABLE IF EXISTS governance.canonical_record;")
    op.execute("DROP TABLE IF EXISTS governance.raw_record;")
    op.execute("DROP TABLE IF EXISTS governance.task_run;")
    op.execute("DROP TABLE IF EXISTS governance.batch;")

    op.execute("CREATE OR REPLACE VIEW governance.batch AS SELECT * FROM public.addr_batch;")
    op.execute("CREATE OR REPLACE VIEW governance.task_run AS SELECT * FROM public.addr_task_run;")
    op.execute("CREATE OR REPLACE VIEW governance.raw_record AS SELECT * FROM public.addr_raw;")
    op.execute("CREATE OR REPLACE VIEW governance.canonical_record AS SELECT * FROM public.addr_canonical;")
    op.execute("CREATE OR REPLACE VIEW governance.review AS SELECT * FROM public.addr_review;")
    op.execute("CREATE OR REPLACE VIEW governance.ruleset AS SELECT * FROM public.addr_ruleset;")
    op.execute("CREATE OR REPLACE VIEW governance.change_request AS SELECT * FROM public.addr_change_request;")
    op.execute("CREATE OR REPLACE VIEW governance.observation_event AS SELECT * FROM public.addr_observation_event;")
    op.execute("CREATE OR REPLACE VIEW governance.observation_metric AS SELECT * FROM public.addr_observation_metric;")
    op.execute("CREATE OR REPLACE VIEW governance.alert_event AS SELECT * FROM public.addr_alert_event;")
    op.execute("CREATE OR REPLACE VIEW audit.event_log AS SELECT * FROM public.addr_audit_event;")
    op.execute("CREATE OR REPLACE VIEW audit.api_audit_log AS SELECT * FROM public.api_audit_log;")
