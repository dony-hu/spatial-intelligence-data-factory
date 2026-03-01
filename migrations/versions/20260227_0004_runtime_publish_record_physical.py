"""runtime publish_record physical table

Revision ID: 20260227_0004
Revises: 20260227_0003
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op


revision = "20260227_0004"
down_revision = "20260227_0003"
branch_labels = None
depends_on = None


_CREATE_COLUMNS_SQL = """
    publish_id VARCHAR(64) PRIMARY KEY,
    workpackage_id VARCHAR(128) NOT NULL,
    version VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    evidence_ref TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    bundle_path TEXT,
    published_by VARCHAR(128),
    confirmation_user VARCHAR(128),
    confirmation_decision VARCHAR(128),
    confirmation_timestamp TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workpackage_id, version)
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS runtime;")

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'runtime' AND c.relname = 'publish_record' AND c.relkind IN ('v', 'm')
          ) THEN
            EXECUTE 'DROP VIEW runtime.publish_record';
          END IF;
        END
        $$;
        """
    )

    op.execute(f"CREATE TABLE IF NOT EXISTS runtime.publish_record ({_CREATE_COLUMNS_SQL});")

    op.execute(
        """
        INSERT INTO runtime.publish_record (
            publish_id, workpackage_id, version, status, evidence_ref, published_at,
            bundle_path, published_by, confirmation_user, confirmation_decision,
            confirmation_timestamp, created_at, updated_at
        )
        SELECT
            publish_id, workpackage_id, version, status, evidence_ref, published_at,
            bundle_path, published_by, confirmation_user, confirmation_decision,
            confirmation_timestamp, created_at, updated_at
        FROM public.addr_workpackage_publish
        ON CONFLICT (workpackage_id, version) DO NOTHING;
        """
    )

    op.execute(
        """
        DO $$
        DECLARE relkind_char "char";
        BEGIN
          SELECT c.relkind
          INTO relkind_char
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE n.nspname = 'public' AND c.relname = 'addr_workpackage_publish'
          LIMIT 1;

          IF relkind_char IN ('v', 'm') THEN
            EXECUTE 'DROP VIEW public.addr_workpackage_publish';
          ELSIF relkind_char = 'r' THEN
            EXECUTE 'DROP TABLE public.addr_workpackage_publish';
          END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE VIEW public.addr_workpackage_publish AS
        SELECT
            publish_id, workpackage_id, version, status, evidence_ref, published_at,
            bundle_path, published_by, confirmation_user, confirmation_decision,
            confirmation_timestamp, created_at, updated_at
        FROM runtime.publish_record;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE relkind_char "char";
        BEGIN
          SELECT c.relkind
          INTO relkind_char
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE n.nspname = 'public' AND c.relname = 'addr_workpackage_publish'
          LIMIT 1;

          IF relkind_char IN ('v', 'm') THEN
            EXECUTE 'DROP VIEW public.addr_workpackage_publish';
          ELSIF relkind_char = 'r' THEN
            EXECUTE 'DROP TABLE public.addr_workpackage_publish';
          END IF;
        END
        $$;
        """
    )
    op.execute(f"CREATE TABLE IF NOT EXISTS public.addr_workpackage_publish ({_CREATE_COLUMNS_SQL});")

    op.execute(
        """
        INSERT INTO public.addr_workpackage_publish (
            publish_id, workpackage_id, version, status, evidence_ref, published_at,
            bundle_path, published_by, confirmation_user, confirmation_decision,
            confirmation_timestamp, created_at, updated_at
        )
        SELECT
            publish_id, workpackage_id, version, status, evidence_ref, published_at,
            bundle_path, published_by, confirmation_user, confirmation_decision,
            confirmation_timestamp, created_at, updated_at
        FROM runtime.publish_record
        ON CONFLICT (workpackage_id, version) DO NOTHING;
        """
    )

    op.execute("DROP TABLE IF EXISTS runtime.publish_record;")
    op.execute("CREATE OR REPLACE VIEW runtime.publish_record AS SELECT * FROM public.addr_workpackage_publish;")
