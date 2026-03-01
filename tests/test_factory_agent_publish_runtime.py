import os
from pathlib import Path


from packages.factory_agent.agent import FactoryAgent
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def test_publish_blocked_when_bundle_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    agent = FactoryAgent()
    result = agent.converse("发布 demo-v1.0.0 到 runtime")
    assert result["status"] == "blocked"
    assert result["action"] == "publish_workpackage"
    assert result["reason"] == "workpackage_not_found"


def test_publish_success_with_version_and_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = Path("workpackages/bundles/demo-v1.0.0")
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "workpackage.json").write_text(
        '{"name":"demo","version":"v1.0.0","sources":["gaode","baidu"]}',
        encoding="utf-8",
    )
    (bundle / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    (bundle / "skills").mkdir(exist_ok=True)
    (bundle / "observability").mkdir(exist_ok=True)

    agent = FactoryAgent()
    result = agent.converse("发布 demo-v1.0.0 到 runtime")
    assert result["status"] == "ok"
    assert result["action"] == "publish_workpackage"
    assert result["runtime"]["status"] == "published"
    assert result["runtime"]["version"] == "v1.0.0"
    assert result["runtime"]["evidence_ref"].endswith(".json")
    assert result["runtime"]["execution"]["status"] == "success"
    assert result["runtime"]["execution"]["return_code"] == 0
    assert result["runtime"]["execution"]["report"].endswith("publish_execution_report.json")
    saved = REPOSITORY.get_workpackage_publish("demo-v1.0.0", "v1.0.0")
    assert saved is not None
    assert saved["status"] == "published"


def test_publish_blocked_when_runtime_execution_failed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = Path("workpackages/bundles/demo-fail-v1.0.0")
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "workpackage.json").write_text(
        '{"name":"demo-fail","version":"v1.0.0","sources":["gaode"]}',
        encoding="utf-8",
    )
    (bundle / "entrypoint.sh").write_text("#!/usr/bin/env bash\nexit 9\n", encoding="utf-8")
    (bundle / "skills").mkdir(exist_ok=True)
    (bundle / "observability").mkdir(exist_ok=True)

    agent = FactoryAgent()
    result = agent.converse("发布 demo-fail-v1.0.0 到 runtime")
    assert result["status"] == "blocked"
    assert result["action"] == "publish_workpackage"
    assert result["reason"] == "runtime_execution_failed"

    saved = REPOSITORY.get_workpackage_publish("demo-fail-v1.0.0", "v1.0.0")
    assert saved is not None
    assert saved["status"] == "blocked"
