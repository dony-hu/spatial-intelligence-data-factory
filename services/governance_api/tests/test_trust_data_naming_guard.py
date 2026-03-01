from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_runtime_paths_use_trust_data_instead_of_trust_db() -> None:
    files = [
        PROJECT_ROOT / "packages/trust_hub/__init__.py",
        PROJECT_ROOT / "services/governance_api/app/routers/ops.py",
        PROJECT_ROOT / "services/governance_api/app/routers/lab.py",
        PROJECT_ROOT / "scripts/run_address_governance_mvp_acceptance.py",
    ]
    for path in files:
        content = path.read_text(encoding="utf-8")
        assert "trust_db" not in content, f"{path} still references trust_db"
