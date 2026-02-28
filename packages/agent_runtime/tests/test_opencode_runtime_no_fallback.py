import pytest

from packages.agent_runtime.adapters.opencode_runtime import OpenCodeRuntime


def test_run_prompt_uses_run_subcommand_and_json_format(monkeypatch) -> None:
    runtime = OpenCodeRuntime()
    captured = {}

    class _FakeResult:
        stdout = '{"strategy":"auto_accept","confidence":0.9}'

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return _FakeResult()

    monkeypatch.setattr("subprocess.run", _fake_run)

    runtime._run_opencode_prompt("hello")
    assert captured["cmd"] == [
        runtime._opencode_bin,
        "run",
        "hello",
        "--format",
        "json",
        "--model",
        "opencode/gpt-5-nano",
    ]
    assert captured["kwargs"]["check"] is True
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["timeout"] == 300


def test_run_prompt_timeout_can_be_overridden_by_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENCODE_TIMEOUT_SEC", "480")
    runtime = OpenCodeRuntime()
    captured = {}

    class _FakeResult:
        stdout = '{"strategy":"auto_accept","confidence":0.9}'

    def _fake_run(cmd, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return _FakeResult()

    monkeypatch.setattr("subprocess.run", _fake_run)
    runtime._run_opencode_prompt("hello")
    assert captured["timeout"] == 480


def test_run_prompt_model_can_be_overridden_by_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENCODE_MODEL", "alibaba-cn/qwen-plus")
    runtime = OpenCodeRuntime()
    captured = {}

    class _FakeResult:
        stdout = '{"strategy":"auto_accept","confidence":0.9}'

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeResult()

    monkeypatch.setattr("subprocess.run", _fake_run)
    runtime._run_opencode_prompt("hello")
    assert captured["cmd"][-2:] == ["--model", "alibaba-cn/qwen-plus"]


def test_parse_output_supports_ndjson_text_events() -> None:
    runtime = OpenCodeRuntime()
    raw = "\n".join(
        [
            '{"type":"step_start","part":{"type":"step-start"}}',
            '{"type":"text","part":{"type":"text","text":"{\\"strategy\\":\\"auto_accept\\",\\"confidence\\":0.91}"}}',
            '{"type":"step_finish","part":{"type":"step-finish"}}',
        ]
    )
    parsed = runtime._parse_opencode_output(raw)
    assert parsed["strategy"] == "auto_accept"
    assert parsed["confidence"] == 0.91


def test_parse_output_supports_fenced_json_in_text_event() -> None:
    runtime = OpenCodeRuntime()
    raw = "\n".join(
        [
            '{"type":"step_start","part":{"type":"step-start"}}',
            '{"type":"text","part":{"type":"text","text":"```json\\n{\\"strategy\\":\\"standardize\\",\\"confidence\\":0.95}\\n```"}}',
            '{"type":"step_finish","part":{"type":"step-finish"}}',
        ]
    )
    parsed = runtime._parse_opencode_output(raw)
    assert parsed["strategy"] == "standardize"
    assert parsed["confidence"] == 0.95


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
