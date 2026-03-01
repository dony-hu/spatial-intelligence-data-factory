from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_trustdb_persister_uses_trust_data_schema() -> None:
    content = (
        PROJECT_ROOT / "services/trust_data_hub/app/repositories/trustdb_persister.py"
    ).read_text(encoding="utf-8")
    assert "trust_db." not in content
    assert "trust_data." in content
