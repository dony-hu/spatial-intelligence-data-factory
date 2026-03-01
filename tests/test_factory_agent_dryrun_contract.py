from pathlib import Path

from packages.factory_agent.agent import FactoryAgent


def test_dryrun_blocked_when_workpackage_missing() -> None:
    agent = FactoryAgent()
    result = agent.converse("试运行 not-exists-v1.0.0")
    assert result["status"] == "blocked"
    assert result["action"] == "dryrun_workpackage"
    assert result["reason"] == "workpackage_not_found"


def test_dryrun_blocked_when_workpackage_config_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = Path("workpackages/bundles/demo-v1.0.0")
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")

    agent = FactoryAgent()
    result = agent.converse("试运行 demo-v1.0.0")
    assert result["status"] == "blocked"
    assert result["action"] == "dryrun_workpackage"
    assert result["reason"] == "workpackage_config_missing"


def test_dryrun_returns_summary_when_contract_valid(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = Path("workpackages/bundles/demo-v1.0.0")
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "workpackage.json").write_text(
        '{"name":"demo","version":"v1.0.0","sources":["gaode","baidu"]}',
        encoding="utf-8",
    )
    (bundle / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")

    agent = FactoryAgent()
    result = agent.converse("试运行 demo-v1.0.0")
    assert result["status"] == "ok"
    assert result["action"] == "dryrun_workpackage"
    assert result["dryrun"]["status"] == "success"
    assert result["dryrun"]["input_summary"]["bundle_name"] == "demo-v1.0.0"
    assert "observability" in result["dryrun"]["artifacts"]


def test_dryrun_blocked_when_entrypoint_execution_failed(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bundle = Path("workpackages/bundles/demo-fail-v1.0.0")
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "workpackage.json").write_text(
        '{"name":"demo-fail","version":"v1.0.0","sources":["gaode"]}',
        encoding="utf-8",
    )
    (bundle / "entrypoint.sh").write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")

    agent = FactoryAgent()
    result = agent.converse("试运行 demo-fail-v1.0.0")
    assert result["status"] == "blocked"
    assert result["action"] == "dryrun_workpackage"
    assert result["reason"] == "dryrun_execution_failed"
