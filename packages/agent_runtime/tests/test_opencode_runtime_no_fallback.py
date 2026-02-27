import pytest

from packages.agent_runtime.adapters.opencode_runtime import OpenCodeRuntime


def test_run_task_blocks_when_opencode_unavailable(monkeypatch) -> None:
    runtime = OpenCodeRuntime()
    monkeypatch.setattr(runtime, "_ensure_opencode_available", lambda: False)

    with pytest.raises(RuntimeError, match="blocked"):
        runtime.run_task(task_context={"task_id": "t-no-opencode"}, ruleset={"ruleset_id": "default"})


def test_run_task_blocks_when_response_invalid(monkeypatch) -> None:
    runtime = OpenCodeRuntime()
    monkeypatch.setattr(runtime, "_ensure_opencode_available", lambda: True)
    monkeypatch.setattr(runtime, "_run_opencode_prompt", lambda _prompt: "not-json")

    with pytest.raises(RuntimeError, match="blocked"):
        runtime.run_task(task_context={"task_id": "t-invalid"}, ruleset={"ruleset_id": "default"})
