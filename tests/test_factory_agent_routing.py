from __future__ import annotations

from packages.factory_agent.agent import FactoryAgent
from packages.factory_agent.routing import detect_agent_intent


def test_detect_agent_intent_matrix() -> None:
    assert detect_agent_intent("存储高德 API Key 为 abc") == "store_api_key"
    assert detect_agent_intent("列出工作包") == "list_workpackages"
    assert detect_agent_intent("query workpackage demo-v1.0.0") == "query_workpackage"
    assert detect_agent_intent("试运行 demo-v1.0.0") == "dryrun_workpackage"
    assert detect_agent_intent("publish demo-v1.0.0 runtime") == "publish_workpackage"
    assert detect_agent_intent("发布 demo-v1.0.0 到 runtime") == "publish_workpackage"
    assert detect_agent_intent("列出数据源") == "list_sources"
    assert detect_agent_intent("generate workpackage") == "generate_workpackage"
    assert detect_agent_intent("请生成地址治理 MVP 方案") == "confirm_requirement"
    assert (
        detect_agent_intent("数据源使用顺丰地图 API；目标是先跑通预验证再发布。")
        == "confirm_requirement"
    )


def test_converse_dispatches_by_detected_intent(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    agent = FactoryAgent()
    monkeypatch.setattr(agent, "_handle_store_api_key", lambda _p: {"action": "store_api_key"})
    monkeypatch.setattr(agent, "_handle_list_workpackages", lambda: {"action": "list_workpackages"})
    monkeypatch.setattr(agent, "_handle_query_workpackage", lambda _p: {"action": "query_workpackage"})
    monkeypatch.setattr(agent, "_handle_dryrun_workpackage", lambda _p: {"action": "dryrun_workpackage"})
    monkeypatch.setattr(agent, "_handle_publish_workpackage", lambda _p: {"action": "publish_workpackage"})
    monkeypatch.setattr(agent, "_handle_list_sources", lambda: {"action": "list_sources"})
    monkeypatch.setattr(agent, "_handle_generate_workpackage", lambda _p: {"action": "generate_workpackage"})
    monkeypatch.setattr(agent, "_handle_requirement_confirmation", lambda _p: {"action": "confirm_requirement"})

    assert agent.converse("存储高德 API Key 为 abc")["action"] == "store_api_key"
    assert agent.converse("列出工作包")["action"] == "list_workpackages"
    assert agent.converse("query workpackage demo-v1.0.0")["action"] == "query_workpackage"
    assert agent.converse("试运行 demo-v1.0.0")["action"] == "dryrun_workpackage"
    assert agent.converse("publish demo-v1.0.0 runtime")["action"] == "publish_workpackage"
    assert agent.converse("发布 demo-v1.0.0 到 runtime")["action"] == "publish_workpackage"
    assert agent.converse("列出数据源")["action"] == "list_sources"
    assert agent.converse("generate workpackage")["action"] == "generate_workpackage"
    assert agent.converse("请生成地址治理 MVP 方案")["action"] == "confirm_requirement"
