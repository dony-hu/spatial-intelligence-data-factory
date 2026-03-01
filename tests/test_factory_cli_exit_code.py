import argparse
import pytest

from scripts.factory_cli import _execute_command


class _StubSession:
    def __init__(self, response):
        self._response = response
        self.last_prompt = ""

    def chat(self, prompt):
        self.last_prompt = prompt
        return self._response


def test_generate_returns_nonzero_when_blocked() -> None:
    args = argparse.Namespace(command="generate", prompt="请生成地址治理 MVP 方案")
    code = _execute_command(args, _StubSession({"status": "blocked", "message": "llm blocked"}))
    assert code == 2


def test_generate_returns_zero_when_ok() -> None:
    args = argparse.Namespace(command="generate", prompt="请生成地址治理 MVP 方案")
    code = _execute_command(args, _StubSession({"status": "ok", "message": "done"}))
    assert code == 0


def test_confirm_command_routes_to_chat_prompt() -> None:
    session = _StubSession({"status": "ok", "message": "done"})
    args = argparse.Namespace(command="confirm", prompt="确认地址治理需求")
    code = _execute_command(args, session)
    assert code == 0
    assert session.last_prompt == "确认地址治理需求"


def test_dryrun_command_returns_nonzero_when_blocked() -> None:
    session = _StubSession({"status": "blocked", "message": "dryrun blocked"})
    args = argparse.Namespace(command="dryrun", workpackage="demo-v1.0.0")
    code = _execute_command(args, session)
    assert code == 2
    assert "试运行 demo-v1.0.0" == session.last_prompt


def test_publish_command_returns_zero_when_ok() -> None:
    session = _StubSession({"status": "ok", "message": "publish ok"})
    args = argparse.Namespace(command="publish", workpackage="demo-v1.0.0")
    code = _execute_command(args, session)
    assert code == 0
    assert "发布 demo-v1.0.0 到 runtime" == session.last_prompt


def test_publish_command_emits_cli_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _StubSession({"status": "ok", "message": "publish ok"})
    args = argparse.Namespace(command="publish", workpackage="demo-v1.0.0")
    captured: list[dict] = []

    monkeypatch.setattr(
        "scripts.factory_cli._record_cli_observation",
        lambda **kwargs: captured.append(kwargs),
    )
    code = _execute_command(args, session)
    assert code == 0
    assert captured
    assert str(captured[0].get("event_type") or "") == "workpackage_created"
    assert str(captured[0].get("workpackage_id") or "") == "demo-v1.0.0"
