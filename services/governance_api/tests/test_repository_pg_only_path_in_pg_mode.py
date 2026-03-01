from __future__ import annotations

import importlib


def test_get_workpackage_publish_uses_pg_only_path_in_pg_mode(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
    mod = importlib.reload(mod)
    GovernanceRepository = mod.GovernanceRepository
    repo = GovernanceRepository()

    repo._memory.workpackage_publishes["wp-1::v1"] = {
        "workpackage_id": "wp-1",
        "version": "v1",
        "status": "published",
    }
    monkeypatch.setattr(repo, "_query", lambda *_args, **_kwargs: [])
    assert repo.get_workpackage_publish("wp-1", "v1") is None


def test_list_workpackage_publishes_uses_pg_only_path_in_pg_mode(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
    mod = importlib.reload(mod)
    GovernanceRepository = mod.GovernanceRepository
    repo = GovernanceRepository()

    repo._memory.workpackage_publishes["wp-2::v2"] = {
        "workpackage_id": "wp-2",
        "version": "v2",
        "status": "published",
    }
    monkeypatch.setattr(repo, "_query", lambda *_args, **_kwargs: [])
    assert repo.list_workpackage_publishes(workpackage_id="wp-2", limit=20) == []


def test_get_task_uses_pg_only_path_in_pg_mode(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
    mod = importlib.reload(mod)
    GovernanceRepository = mod.GovernanceRepository
    repo = GovernanceRepository()
    repo._memory.tasks["task-1"] = {"task_id": "task-1", "status": "SUCCEEDED"}
    monkeypatch.setattr(repo, "_query", lambda *_args, **_kwargs: [])
    assert repo.get_task("task-1") is None


def test_list_tasks_uses_pg_only_path_in_pg_mode(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
    mod = importlib.reload(mod)
    GovernanceRepository = mod.GovernanceRepository
    repo = GovernanceRepository()
    repo._memory.tasks["task-2"] = {"task_id": "task-2", "status": "FAILED"}
    monkeypatch.setattr(repo, "_query", lambda *_args, **_kwargs: [])
    assert repo.list_tasks(limit=20) == []


def test_get_results_uses_pg_only_path_in_pg_mode(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
    mod = importlib.reload(mod)
    GovernanceRepository = mod.GovernanceRepository
    repo = GovernanceRepository()
    repo._memory.results["task-3"] = [{"raw_id": "r1", "canon_text": "x"}]
    monkeypatch.setattr(repo, "_query", lambda *_args, **_kwargs: [])
    assert repo.get_results("task-3") == []


def test_get_review_and_ruleset_use_pg_only_path_in_pg_mode(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
    mod = importlib.import_module("services.governance_api.app.repositories.governance_repository")
    mod = importlib.reload(mod)
    GovernanceRepository = mod.GovernanceRepository
    repo = GovernanceRepository()
    repo._memory.reviews["task-4"] = {"review_status": "approved"}
    repo._memory.rulesets["rule-x"] = {"ruleset_id": "rule-x"}
    monkeypatch.setattr(repo, "_query", lambda *_args, **_kwargs: [])
    assert repo.get_review("task-4") is None
    assert repo.get_ruleset("rule-x") is None
