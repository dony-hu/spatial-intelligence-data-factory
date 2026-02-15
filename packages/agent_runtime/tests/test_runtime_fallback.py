from packages.agent_runtime.adapters.legacy_runtime import LegacyRuntime


def test_legacy_runtime_fallback_contract() -> None:
    runtime = LegacyRuntime()
    result = runtime.run_task(task_context={"task_id": "t2"}, ruleset={"ruleset_id": "default"})
    assert result.strategy == "rule_only"
    assert result.agent_run_id.startswith("legacy_")
