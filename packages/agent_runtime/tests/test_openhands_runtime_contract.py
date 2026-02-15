from packages.agent_runtime.adapters.openhands_runtime import OpenHandsRuntime


def test_openhands_runtime_contract(monkeypatch) -> None:
    runtime = OpenHandsRuntime(config_path="/tmp/not-exists.json")

    monkeypatch.setenv("LLM_ENDPOINT", "https://example.com/v1/chat/completions")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def fake_post(_config, _messages):
        return {
            "id": "chatcmpl-test-001",
            "model": "mock-model",
            "choices": [
                {
                    "message": {
                        "content": '{"strategy":"auto_accept","confidence":0.88,"canonical":{"canon_text":"深圳市南山区"},"actions":[{"name":"save"}],"evidence":{"items":[{"source":"llm"}]}}'
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    monkeypatch.setattr(runtime, "_post_chat_completion", fake_post)

    result = runtime.run_task(task_context={"task_id": "t1"}, ruleset={"ruleset_id": "default"})
    assert result.strategy
    assert 0 <= result.confidence <= 1
    assert result.agent_run_id
    assert result.strategy == "auto_accept"
    assert result.canonical.get("canon_text") == "深圳市南山区"
    assert any(item.get("runtime") == "openhands" for item in result.evidence.get("items", []))


def test_openhands_runtime_fallback_when_missing_key(monkeypatch) -> None:
    runtime = OpenHandsRuntime(config_path="/tmp/not-exists.json")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_ENDPOINT", raising=False)
    result = runtime.run_task(task_context={"task_id": "t2"}, ruleset={"ruleset_id": "default"})
    assert result.strategy == "human_required"
    assert any(item.get("message") == "llm_call_fallback" for item in result.evidence.get("items", []))
