from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_repository_no_longer_references_public_addr_tables() -> None:
    content = (PROJECT_ROOT / "services/governance_api/app/repositories/governance_repository.py").read_text(encoding="utf-8")
    forbidden = [
        "addr_batch",
        "addr_task_run",
        "addr_raw",
        "addr_canonical",
        "addr_review",
        "addr_ruleset",
        "addr_change_request",
        "addr_observation_event",
        "addr_observation_metric",
        "addr_alert_event",
        "addr_audit_event",
    ]
    for marker in forbidden:
        assert marker not in content, f"repository should use governance/audit domain tables instead of {marker}"
