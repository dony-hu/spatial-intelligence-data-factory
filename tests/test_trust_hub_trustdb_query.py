from __future__ import annotations

import sqlite3

import pytest

from packages.trust_hub import TrustHub


def test_query_trust_tables_blocked_without_database_url(tmp_path) -> None:
    hub = TrustHub(storage_path=tmp_path / "trust_hub.json", database_url="")
    with pytest.raises(ValueError, match="blocked"):
        hub.list_trust_meta_sources(namespace_id="cn_demo", limit=10)


def test_query_trust_meta_and_trust_db_with_sqlite(tmp_path) -> None:
    db_path = tmp_path / "trust_runtime.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE trust_meta_source_registry (
                namespace_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                source_name TEXT,
                source_type TEXT,
                authority_score REAL,
                freshness_sla TEXT,
                coverage_json TEXT,
                quality_json TEXT,
                status TEXT,
                owner TEXT,
                created_at TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE trust_db_admin_division (
                namespace_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                division_id TEXT NOT NULL,
                name TEXT,
                level TEXT,
                parent_id TEXT,
                adcode TEXT,
                geom TEXT,
                attrs_json TEXT,
                valid_from TEXT,
                valid_to TEXT,
                snapshot_id TEXT
            );
            """
        )
        conn.execute(
            """
            INSERT INTO trust_meta_source_registry (
                namespace_id, source_id, source_name, source_type, authority_score, status, owner, created_at
            ) VALUES ('cn_demo', 'gaode', '高德POI', 'api', 0.93, 'active', 'owner_a', '2026-02-27T12:00:00Z');
            """
        )
        conn.execute(
            """
            INSERT INTO trust_db_admin_division (
                namespace_id, source_id, division_id, name, level, adcode, snapshot_id
            ) VALUES ('cn_demo', 'gaode', 'div_330106', '西湖区', 'district', '330106', 'snap_1');
            """
        )
        conn.commit()
    finally:
        conn.close()

    hub = TrustHub(storage_path=tmp_path / "trust_hub.json", database_url=f"sqlite:///{db_path}")
    meta_rows = hub.list_trust_meta_sources(namespace_id="cn_demo", limit=10)
    assert len(meta_rows) == 1
    assert meta_rows[0]["source_id"] == "gaode"
    trust_rows = hub.list_trust_db_admin_division(namespace_id="cn_demo", limit=10)
    assert len(trust_rows) == 1
    assert trust_rows[0]["division_id"] == "div_330106"
