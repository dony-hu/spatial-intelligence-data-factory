from __future__ import annotations

from pathlib import Path


def test_gitignore_covers_local_env_noise_and_acceptance_outputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    content = (repo_root / ".gitignore").read_text(encoding="utf-8")
    required_patterns = [
        ".venv.broken.*/",
        "output/acceptance/",
        "output/logs/",
    ]
    for pattern in required_patterns:
        assert pattern in content


def test_repo_hygiene_script_keeps_basic_hygiene_header() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = (repo_root / "scripts" / "check_repo_hygiene.sh").read_text(encoding="utf-8")
    assert "[check] repo hygiene" in script


def test_repo_hygiene_script_has_sqlite_reflow_guard() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = (repo_root / "scripts" / "check_repo_hygiene.sh").read_text(encoding="utf-8")
    assert "sqlite://" in script
    assert "init_governance_sqlite" in script
    assert "services packages scripts tests" in script
