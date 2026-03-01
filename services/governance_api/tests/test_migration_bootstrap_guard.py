from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_init_migration_contains_observability_and_publish_tables() -> None:
    content = (
        PROJECT_ROOT / "migrations/versions/20260214_0001_init_addr_governance.py"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS addr_workpackage_publish" in content
    assert "CREATE TABLE IF NOT EXISTS addr_observation_event" in content
    assert "CREATE TABLE IF NOT EXISTS addr_observation_metric" in content
    assert "CREATE TABLE IF NOT EXISTS addr_alert_event" in content


def test_trust_meta_migration_bootstraps_trust_db_tables() -> None:
    content = (
        PROJECT_ROOT / "migrations/versions/bd518515a0fe_init_trust_meta_tables_with_composite_pk.py"
    ).read_text(encoding="utf-8")
    assert "CREATE SCHEMA IF NOT EXISTS trust_meta" in content
    assert "CREATE SCHEMA IF NOT EXISTS trust_db" in content
    assert "CREATE TABLE IF NOT EXISTS trust_db.admin_division" in content
    assert "CREATE TABLE IF NOT EXISTS trust_db.road_index" in content
    assert "CREATE TABLE IF NOT EXISTS trust_db.poi_index" in content


def test_runtime_publish_migration_handles_view_or_table_cleanup() -> None:
    content = (
        PROJECT_ROOT / "migrations/versions/20260227_0004_runtime_publish_record_physical.py"
    ).read_text(encoding="utf-8")
    assert "DROP TABLE public.addr_workpackage_publish" in content
    assert "DROP VIEW public.addr_workpackage_publish" in content
