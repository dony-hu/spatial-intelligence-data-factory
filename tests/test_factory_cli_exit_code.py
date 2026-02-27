import argparse

from scripts.factory_cli import _execute_command


class _StubSession:
    def __init__(self, response):
        self._response = response

    def chat(self, _prompt):
        return self._response


def test_generate_returns_nonzero_when_blocked() -> None:
    args = argparse.Namespace(command="generate", prompt="请生成地址治理 MVP 方案")
    code = _execute_command(args, _StubSession({"status": "blocked", "message": "llm blocked"}))
    assert code == 2


def test_generate_returns_zero_when_ok() -> None:
    args = argparse.Namespace(command="generate", prompt="请生成地址治理 MVP 方案")
    code = _execute_command(args, _StubSession({"status": "ok", "message": "done"}))
    assert code == 0
