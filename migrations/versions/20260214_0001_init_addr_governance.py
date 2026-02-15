"""init addr governance

Revision ID: 20260214_0001
Revises:
Create Date: 2026-02-14
"""

from __future__ import annotations

from alembic import op


revision = "20260214_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS addr_batch (
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
        CREATE TABLE IF NOT EXISTS addr_task_run (
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
        CREATE TABLE IF NOT EXISTS addr_raw (
            raw_id VARCHAR(64) PRIMARY KEY,
            batch_id VARCHAR(64) NOT NULL REFERENCES addr_batch(batch_id),
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
        CREATE TABLE IF NOT EXISTS addr_canonical (
            canonical_id VARCHAR(64) PRIMARY KEY,
            raw_id VARCHAR(64) NOT NULL REFERENCES addr_raw(raw_id),
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
        CREATE TABLE IF NOT EXISTS addr_review (
            review_id VARCHAR(64) PRIMARY KEY,
            raw_id VARCHAR(64) NOT NULL REFERENCES addr_raw(raw_id),
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
        CREATE TABLE IF NOT EXISTS addr_ruleset (
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
        CREATE TABLE IF NOT EXISTS api_audit_log (
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
        CREATE TABLE IF NOT EXISTS agent_execution_log (
            execution_id VARCHAR(64) PRIMARY KEY,
            task_id VARCHAR(64) NOT NULL,
            runtime VARCHAR(32) NOT NULL,
            latency_ms INT,
            success BOOLEAN NOT NULL,
            error_type VARCHAR(64),
            trace_id VARCHAR(64),
            agent_run_id VARCHAR(64),
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_addr_raw_hash ON addr_raw(raw_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addr_raw_text_trgm ON addr_raw USING gin(raw_text gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addr_canonical_text_trgm ON addr_canonical USING gin(canon_text gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addr_task_run_status ON addr_task_run(task_id, status);")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_addr_review_status') THEN
                ALTER TABLE addr_review
                    ADD CONSTRAINT chk_addr_review_status
                    CHECK (review_status IN ('approved', 'rejected', 'edited'));
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_addr_task_retry_count') THEN
                ALTER TABLE addr_task_run
                    ADD CONSTRAINT chk_addr_task_retry_count
                    CHECK (retry_count >= 0);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_execution_log;")
    op.execute("DROP TABLE IF EXISTS api_audit_log;")
    op.execute("DROP TABLE IF EXISTS addr_ruleset;")
    op.execute("DROP TABLE IF EXISTS addr_review;")
    op.execute("DROP TABLE IF EXISTS addr_canonical;")
    op.execute("DROP TABLE IF EXISTS addr_raw;")
    op.execute("DROP TABLE IF EXISTS addr_task_run;")
    op.execute("DROP TABLE IF EXISTS addr_batch;")
