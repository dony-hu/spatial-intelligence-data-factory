from __future__ import annotations

from packages.factory_agent.llm_gateway import RequirementLLMGateway


def test_requirement_llm_gateway_calls_agent_cli(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_load_config() -> dict[str, object]:
        captured["load_config_called"] = True
        return {"model": "x"}

    def _fake_run_requirement_query(requirement, config, system_prompt_override=""):
        captured["requirement"] = requirement
        captured["config"] = config
        captured["system_prompt_override"] = system_prompt_override
        return {"status": "ok", "answer": "{}"}

    monkeypatch.setattr("tools.agent_cli.load_config", _fake_load_config)
    monkeypatch.setattr("tools.agent_cli.run_requirement_query", _fake_run_requirement_query)

    gateway = RequirementLLMGateway()
    result = gateway.query("请生成地址治理 MVP 方案")
    assert result["status"] == "ok"
    assert captured.get("load_config_called") is True
    assert captured.get("requirement") == "请生成地址治理 MVP 方案"
    assert "target(string)" in str(captured.get("system_prompt_override") or "")
