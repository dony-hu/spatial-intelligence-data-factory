from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.factory_agent.nanobot_adapter import NanobotAdapter


def _write_temp_llm_config(path: Path, api_key_value: str) -> None:
    payload = {
        "provider": "openai_compatible",
        "endpoint": "https://611996.xyz/v1/chat/completions",
        "model": "gpt-5.3-codex",
        "api_key": api_key_value,
        "timeout_sec": 60,
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_nanobot_adapter_resolves_env_placeholder_api_key(monkeypatch, tmp_path: Path) -> None:
    cfg = tmp_path / "llm_api.json"
    _write_temp_llm_config(cfg, "${LLM_API_KEY}")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-from-env")

    adapter = NanobotAdapter(config_path=cfg)

    assert adapter._settings.get("api_key") == "sk-test-from-env"


def test_nanobot_adapter_raises_when_env_placeholder_unresolved(monkeypatch, tmp_path: Path) -> None:
    cfg = tmp_path / "llm_api.json"
    _write_temp_llm_config(cfg, "${LLM_API_KEY}")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="missing api_key"):
        NanobotAdapter(config_path=cfg)


def test_nanobot_adapter_defaults_to_curl_transport_for_openai_compatible(tmp_path: Path) -> None:
    cfg = tmp_path / "llm_api.json"
    _write_temp_llm_config(cfg, "sk-test")
    adapter = NanobotAdapter(config_path=cfg)
    assert adapter._settings.get("transport") == "curl"


def test_nanobot_adapter_query_via_curl_parses_chat_completions(monkeypatch, tmp_path: Path) -> None:
    cfg = tmp_path / "llm_api.json"
    _write_temp_llm_config(cfg, "sk-test")
    adapter = NanobotAdapter(config_path=cfg)

    class _Proc:
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            {
                "id": "resp_123",
                "object": "chat.completion",
                "model": "gpt-5.3-codex",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "OK"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr("packages.factory_agent.nanobot_adapter.subprocess.run", lambda *args, **kwargs: _Proc())
    result = adapter.chat("请仅回复OK", system_prompt="你是助手", timeout_sec=10, max_tokens=16, temperature=0)

    assert result.get("status") == "ok"
    assert str(result.get("answer") or "") == "OK"
    assert int((result.get("token_usage") or {}).get("total") or 0) == 4


def test_nanobot_adapter_query_via_curl_raises_on_invalid_response(monkeypatch, tmp_path: Path) -> None:
    cfg = tmp_path / "llm_api.json"
    _write_temp_llm_config(cfg, "sk-test")
    adapter = NanobotAdapter(config_path=cfg)

    class _Proc:
        returncode = 0
        stderr = ""
        stdout = '{"id":"x"}'

    monkeypatch.setattr("packages.factory_agent.nanobot_adapter.subprocess.run", lambda *args, **kwargs: _Proc())
    with pytest.raises(RuntimeError, match="missing choices"):
        adapter.chat("hello", timeout_sec=10, max_tokens=16, temperature=0)


def test_nanobot_adapter_query_via_curl_raises_on_process_timeout(monkeypatch, tmp_path: Path) -> None:
    cfg = tmp_path / "llm_api.json"
    _write_temp_llm_config(cfg, "sk-test")
    adapter = NanobotAdapter(config_path=cfg)

    def _raise_timeout(*_args, **_kwargs):
        raise __import__("subprocess").TimeoutExpired(cmd="curl", timeout=10)

    monkeypatch.setattr("packages.factory_agent.nanobot_adapter.subprocess.run", _raise_timeout)
    with pytest.raises(RuntimeError, match="process timeout"):
        adapter.chat("hello", timeout_sec=10, max_tokens=16, temperature=0)
