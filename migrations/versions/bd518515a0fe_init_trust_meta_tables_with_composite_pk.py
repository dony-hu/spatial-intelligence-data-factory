"""init_trust_meta_tables_with_composite_pk

Revision ID: bd518515a0fe
Revises: 20260215_0002
Create Date: 2026-02-16 18:08:20.853795
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'bd518515a0fe'
down_revision = '20260215_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS trust_meta;")
    op.execute("CREATE SCHEMA IF NOT EXISTS trust_db;")

    # 1. source_snapshot
    op.create_table(
        'source_snapshot',
        sa.Column('namespace_id', sa.String(length=64), nullable=False),
        sa.Column('snapshot_id', sa.String(length=64), nullable=False),
        sa.Column('source_name', sa.String(length=128), nullable=False),
        sa.Column('record_count', sa.Integer(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('storage_path', sa.String(length=256), nullable=False),
        sa.Column('format', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('meta_info', JSONB, server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('namespace_id', 'snapshot_id'),
        schema='trust_meta'
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_db.admin_division (
            namespace_id VARCHAR(64) NOT NULL,
            source_id VARCHAR(64) NOT NULL,
            division_id VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            level VARCHAR(32),
            parent_id VARCHAR(64),
            adcode VARCHAR(32),
            snapshot_id VARCHAR(64),
            PRIMARY KEY(namespace_id, source_id, division_id)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_db.place_name_index (
            namespace_id VARCHAR(64) NOT NULL,
            source_id VARCHAR(64) NOT NULL,
            place_id VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            alias_names JSONB DEFAULT '[]'::jsonb,
            category VARCHAR(64),
            adcode VARCHAR(32),
            confidence_hint DOUBLE PRECISION,
            snapshot_id VARCHAR(64),
            PRIMARY KEY(namespace_id, source_id, place_id)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_db.road_index (
            namespace_id VARCHAR(64) NOT NULL,
            source_id VARCHAR(64) NOT NULL,
            road_id VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            alias_names JSONB DEFAULT '[]'::jsonb,
            adcode VARCHAR(32),
            snapshot_id VARCHAR(64),
            PRIMARY KEY(namespace_id, source_id, road_id)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS trust_db.poi_index (
            namespace_id VARCHAR(64) NOT NULL,
            source_id VARCHAR(64) NOT NULL,
            poi_id VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(64),
            adcode VARCHAR(32),
            lon DOUBLE PRECISION,
            lat DOUBLE PRECISION,
            snapshot_id VARCHAR(64),
            PRIMARY KEY(namespace_id, source_id, poi_id)
        );
        """
    )

    # 2. snapshot_quality_report
    op.create_table(
        'snapshot_quality_report',
        sa.Column('report_id', sa.String(length=64), primary_key=True),
        sa.Column('namespace_id', sa.String(length=64), nullable=False),
        sa.Column('snapshot_id', sa.String(length=64), nullable=False),
        sa.Column('ruleset_version', sa.String(length=32), nullable=False),
        sa.Column('total_records', sa.Integer(), nullable=False),
        sa.Column('valid_records', sa.Integer(), nullable=False),
        sa.Column('error_records', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('details', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['namespace_id', 'snapshot_id'],
            ['trust_meta.source_snapshot.namespace_id', 'trust_meta.source_snapshot.snapshot_id']
        ),
        schema='trust_meta'
    )

    # 3. active_release
    op.create_table(
        'active_release',
        sa.Column('namespace_id', sa.String(length=64), primary_key=True),
        sa.Column('active_snapshot_id', sa.String(length=64), nullable=False),
        sa.Column('release_tag', sa.String(length=64), nullable=True),
        sa.Column('promoted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('promoted_by', sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ['namespace_id', 'active_snapshot_id'],
            ['trust_meta.source_snapshot.namespace_id', 'trust_meta.source_snapshot.snapshot_id']
        ),
        schema='trust_meta'
    )

    # 4. snapshot_diff_report
    op.create_table(
        'snapshot_diff_report',
        sa.Column('diff_id', sa.String(length=64), primary_key=True),
        sa.Column('namespace_id', sa.String(length=64), nullable=False),
        sa.Column('base_snapshot_id', sa.String(length=64), nullable=False),
        sa.Column('new_snapshot_id', sa.String(length=64), nullable=False),
        sa.Column('added_count', sa.Integer(), nullable=False),
        sa.Column('removed_count', sa.Integer(), nullable=False),
        sa.Column('modified_count', sa.Integer(), nullable=False),
        sa.Column('diff_summary', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['namespace_id', 'base_snapshot_id'],
            ['trust_meta.source_snapshot.namespace_id', 'trust_meta.source_snapshot.snapshot_id']
        ),
        sa.ForeignKeyConstraint(
            ['namespace_id', 'new_snapshot_id'],
            ['trust_meta.source_snapshot.namespace_id', 'trust_meta.source_snapshot.snapshot_id']
        ),
        schema='trust_meta'
    )

    # 5. validation_replay_run
    op.create_table(
        'validation_replay_run',
        sa.Column('run_id', sa.String(length=64), primary_key=True),
        sa.Column('namespace_id', sa.String(length=64), nullable=False),
        sa.Column('snapshot_id', sa.String(length=64), nullable=False),
        sa.Column('ruleset_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_summary', JSONB, server_default='{}', nullable=False),
        sa.ForeignKeyConstraint(
            ['namespace_id', 'snapshot_id'],
            ['trust_meta.source_snapshot.namespace_id', 'trust_meta.source_snapshot.snapshot_id']
        ),
        schema='trust_meta'
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS trust_db.poi_index;")
    op.execute("DROP TABLE IF EXISTS trust_db.road_index;")
    op.execute("DROP TABLE IF EXISTS trust_db.place_name_index;")
    op.execute("DROP TABLE IF EXISTS trust_db.admin_division;")
    op.drop_table('validation_replay_run', schema='trust_meta')
    op.drop_table('snapshot_diff_report', schema='trust_meta')
    op.drop_table('active_release', schema='trust_meta')
    op.drop_table('snapshot_quality_report', schema='trust_meta')
    op.drop_table('source_snapshot', schema='trust_meta')
