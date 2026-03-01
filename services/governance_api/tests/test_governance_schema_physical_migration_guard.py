from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_governance_audit_physical_migration_exists_and_materializes_tables() -> None:
    path = PROJECT_ROOT / "migrations/versions/20260227_0005_governance_audit_physical_tables.py"
    content = path.read_text(encoding="utf-8")

    assert 'revision = "20260227_0005"' in content
    assert "CREATE TABLE IF NOT EXISTS governance.batch" in content
    assert "CREATE TABLE IF NOT EXISTS governance.task_run" in content
    assert "CREATE TABLE IF NOT EXISTS governance.raw_record" in content
    assert "CREATE TABLE IF NOT EXISTS governance.canonical_record" in content
    assert "CREATE TABLE IF NOT EXISTS governance.review" in content
    assert "CREATE TABLE IF NOT EXISTS governance.ruleset" in content
    assert "CREATE TABLE IF NOT EXISTS governance.change_request" in content
    assert "CREATE TABLE IF NOT EXISTS governance.observation_event" in content
    assert "CREATE TABLE IF NOT EXISTS governance.observation_metric" in content
    assert "CREATE TABLE IF NOT EXISTS governance.alert_event" in content
    assert "CREATE TABLE IF NOT EXISTS audit.event_log" in content
    assert "INSERT INTO governance.batch" in content
    assert "INSERT INTO governance.task_run" in content
    assert "INSERT INTO audit.event_log" in content
