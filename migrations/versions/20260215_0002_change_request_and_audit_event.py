"""add change request and audit event

Revision ID: 20260215_0002
Revises: 20260214_0001
Create Date: 2026-02-15
"""

from __future__ import annotations

from alembic import op


revision = "20260215_0002"
down_revision = "20260214_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS addr_change_request (
            change_id VARCHAR(64) PRIMARY KEY,
            from_ruleset_id VARCHAR(64) NOT NULL REFERENCES addr_ruleset(ruleset_id),
            to_ruleset_id VARCHAR(64) NOT NULL REFERENCES addr_ruleset(ruleset_id),
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
        CREATE TABLE IF NOT EXISTS addr_audit_event (
            event_id VARCHAR(64) PRIMARY KEY,
            event_type VARCHAR(64) NOT NULL,
            caller VARCHAR(128) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            related_change_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_addr_change_request_status ON addr_change_request(status, created_at DESC);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_addr_change_request_to_ruleset ON addr_change_request(to_ruleset_id, created_at DESC);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_addr_audit_event_change ON addr_audit_event(related_change_id, created_at DESC);")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_addr_change_request_status') THEN
                ALTER TABLE addr_change_request
                    ADD CONSTRAINT chk_addr_change_request_status
                    CHECK (status IN ('pending', 'approved', 'rejected'));
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS addr_audit_event;")
    op.execute("DROP TABLE IF EXISTS addr_change_request;")
