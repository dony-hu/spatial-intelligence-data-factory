from packages.factory_agent.agent import FactoryAgent


def test_converse_returns_blocked_when_llm_fails(monkeypatch) -> None:
    agent = FactoryAgent()

    def _raise(_prompt: str):
        raise RuntimeError("llm down")

    monkeypatch.setattr(agent, "_run_requirement_query", _raise)

    result = agent.converse("请生成地址治理 MVP 方案")
    assert result["status"] == "blocked"
    assert result["action"] == "confirm_requirement"
    assert "llm" in str(result.get("reason", "")).lower()


def test_converse_returns_structured_summary_when_llm_ok(monkeypatch) -> None:
    agent = FactoryAgent()
    answer = """
{
  "target": "地址标准化与去重",
  "data_sources": ["gaode_api", "baidu_api"],
  "rule_points": ["结构化解析", "冲突评分"],
  "outputs": ["workpackage", "observability_report"]
}
""".strip()
    monkeypatch.setattr(agent, "_run_requirement_query", lambda _prompt: {"status": "ok", "answer": answer})

    result = agent.converse("请生成地址治理 MVP 方案")
    assert result["status"] == "ok"
    assert result["action"] == "confirm_requirement"
    assert result["summary"]["target"] == "地址标准化与去重"
    assert result["summary"]["data_sources"] == ["gaode_api", "baidu_api"]
