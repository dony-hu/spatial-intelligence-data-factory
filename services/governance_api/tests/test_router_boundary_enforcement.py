from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_core_routers_should_not_directly_use_repository_singleton() -> None:
    targets = [
        "services/governance_api/app/routers/tasks.py",
        "services/governance_api/app/routers/reviews.py",
        "services/governance_api/app/routers/ops.py",
        "services/governance_api/app/routers/observability.py",
        "services/governance_api/app/routers/rulesets.py",
        "services/governance_api/app/routers/manual_review.py",
        "services/governance_api/app/routers/lab.py",
    ]
    for target in targets:
        content = _read(target)
        assert "REPOSITORY" not in content, f"{target} should not reference REPOSITORY directly"


def test_lab_router_should_not_access_repository_memory_internal() -> None:
    content = _read("services/governance_api/app/routers/lab.py")
    assert "REPOSITORY._memory" not in content
