from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_governance_repository_has_no_runtime_auto_ddl_logic() -> None:
    content = (PROJECT_ROOT / "services/governance_api/app/repositories/governance_repository.py").read_text(encoding="utf-8")
    assert "GOVERNANCE_AUTO_DDL" not in content
    assert "CREATE TABLE IF NOT EXISTS" not in content


def test_trust_hub_has_no_runtime_auto_create_table_logic() -> None:
    content = (PROJECT_ROOT / "packages/trust_hub/__init__.py").read_text(encoding="utf-8")
    assert "_ensure_capability_sample_tables" not in content
    assert "CREATE TABLE IF NOT EXISTS" not in content


def test_tc06_line_execution_has_no_runtime_auto_create_table_logic() -> None:
    content = (PROJECT_ROOT / "scripts/line_execution_tc06.py").read_text(encoding="utf-8")
    assert "_ensure_pg_feedback_tables" not in content
    assert "CREATE TABLE IF NOT EXISTS" not in content
