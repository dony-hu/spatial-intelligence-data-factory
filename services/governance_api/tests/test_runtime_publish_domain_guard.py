from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_repository_uses_runtime_publish_record_as_primary_store() -> None:
    content = (PROJECT_ROOT / "services/governance_api/app/repositories/governance_repository.py").read_text(encoding="utf-8")
    assert "runtime.publish_record" in content
    assert "addr_workpackage_publish" not in content


def test_acceptance_script_queries_runtime_publish_record() -> None:
    content = (PROJECT_ROOT / "scripts/run_address_governance_mvp_acceptance.py").read_text(encoding="utf-8")
    assert "runtime.publish_record" in content
    assert "addr_workpackage_publish" not in content
