"""unified schema alignment for governance/runtime/trust_data/audit

Revision ID: 20260227_0003
Revises: bd518515a0fe
Create Date: 2026-02-27
"""

from __future__ import annotations

from alembic import op


revision = "20260227_0003"
down_revision = "bd518515a0fe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Canonical schemas from architecture-unified-pg-multi-schema-v1-2026-02-27.md
    op.execute("CREATE SCHEMA IF NOT EXISTS governance;")
    op.execute("CREATE SCHEMA IF NOT EXISTS runtime;")
    op.execute("CREATE SCHEMA IF NOT EXISTS trust_data;")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit;")

    # Governance domain compatibility views
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

    # Runtime domain compatibility views
    op.execute("CREATE OR REPLACE VIEW runtime.publish_record AS SELECT * FROM public.addr_workpackage_publish;")

    # Audit domain compatibility views
    op.execute("CREATE OR REPLACE VIEW audit.event_log AS SELECT * FROM public.addr_audit_event;")
    op.execute("CREATE OR REPLACE VIEW audit.api_audit_log AS SELECT * FROM public.api_audit_log;")

    # trust_data aligns with existing trust_db schema in current codebase
    op.execute("CREATE OR REPLACE VIEW trust_data.admin_division AS SELECT * FROM trust_db.admin_division;")
    op.execute("CREATE OR REPLACE VIEW trust_data.road_index AS SELECT * FROM trust_db.road_index;")
    op.execute("CREATE OR REPLACE VIEW trust_data.poi_index AS SELECT * FROM trust_db.poi_index;")
    op.execute("CREATE OR REPLACE VIEW trust_data.place_name_index AS SELECT * FROM trust_db.place_name_index;")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS trust_data.place_name_index;")
    op.execute("DROP VIEW IF EXISTS trust_data.poi_index;")
    op.execute("DROP VIEW IF EXISTS trust_data.road_index;")
    op.execute("DROP VIEW IF EXISTS trust_data.admin_division;")
    op.execute("DROP VIEW IF EXISTS audit.api_audit_log;")
    op.execute("DROP VIEW IF EXISTS audit.event_log;")
    op.execute("DROP VIEW IF EXISTS runtime.publish_record;")
    op.execute("DROP VIEW IF EXISTS governance.alert_event;")
    op.execute("DROP VIEW IF EXISTS governance.observation_metric;")
    op.execute("DROP VIEW IF EXISTS governance.observation_event;")
    op.execute("DROP VIEW IF EXISTS governance.change_request;")
    op.execute("DROP VIEW IF EXISTS governance.ruleset;")
    op.execute("DROP VIEW IF EXISTS governance.review;")
    op.execute("DROP VIEW IF EXISTS governance.canonical_record;")
    op.execute("DROP VIEW IF EXISTS governance.raw_record;")
    op.execute("DROP VIEW IF EXISTS governance.task_run;")
    op.execute("DROP VIEW IF EXISTS governance.batch;")
