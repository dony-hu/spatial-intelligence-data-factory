from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_scripts_do_not_query_legacy_addr_tables() -> None:
    files = [
        PROJECT_ROOT / "scripts/collect_governance_metrics.py",
        PROJECT_ROOT / "scripts/seed_manual_review_pg_data.py",
        PROJECT_ROOT / "scripts/run_governance_e2e_dual_real_local.sh",
        PROJECT_ROOT / "scripts/init_unified_pg_schema.py",
    ]
    forbidden = [
        "addr_batch",
        "addr_task_run",
        "addr_raw",
        "addr_canonical",
        "addr_review",
        "addr_ruleset",
        "addr_change_request",
        "addr_audit_event",
        "public.addr_",
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in content, f"{path} still references legacy table marker: {marker}"
