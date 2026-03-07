from __future__ import annotations

import json
from pathlib import Path

from packages.factory_agent.agent import FactoryAgent


class _FakeTrustHub:
    def list_sources(self):
        return []


def test_factory_agent_converse_writes_runtime_trace_file_and_returns_trace_payload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("packages.factory_agent.agent.TrustHub", _FakeTrustHub)
    agent = FactoryAgent()
    monkeypatch.setattr(
        agent,
        "_run_general_chat_query",
        lambda _prompt: {"answer": "可以，先从输入字段和质量规则开始。"},
    )

    result = agent.converse("我们先聊聊数据治理目标", session_id="trace-session-001")

    traces = result.get("nanobot_traces") or {}
    client_logs = traces.get("client_nanobot") or []
    assert len(client_logs) >= 2
    assert str(client_logs[0].get("direction") or "") == "client->nanobot"
    assert str(client_logs[1].get("direction") or "") == "nanobot->client"

    trace_log_path = Path(str(result.get("trace_log_path") or ""))
    assert trace_log_path.exists()
    lines = [json.loads(line) for line in trace_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 2
    assert {str(item.get("channel") or "") for item in lines}.issuperset({"client_nanobot"})

    memory = result.get("memory_objects") or {}
    assert isinstance(memory, dict)
    boot_context = memory.get("boot_context") or {}
    assert str((boot_context.get("role_contract") or {}).get("agent_name") or "") == "nanobot"
    assert bool((boot_context.get("boundary_contract") or {}).get("forbidden"))
    discovery = memory.get("discovery_facts") or {}
    assert "数据治理目标" in str(discovery.get("goal_text") or "")
    assert isinstance(memory.get("timeline"), list)


def test_factory_agent_generate_workpackage_returns_nanobot_opencode_trace_events(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("packages.factory_agent.agent.TrustHub", _FakeTrustHub)
    agent = FactoryAgent()

    def _fake_blueprint_query(_prompt: str, _context: dict, _feedback=None):
        answer = {
            "workpackage": {"name": "trace-case", "version": "v1.0.0", "objective": "地址治理"},
            "architecture_context": {"factory_architecture": {"layers": ["agent", "opencode"]}, "runtime_env": {"python": "3.11"}},
            "io_contract": {"input_schema": {"type": "object"}, "output_schema": {"type": "object"}},
            "api_plan": {"registered_apis_used": [], "missing_apis": []},
            "execution_plan": {"steps": ["plan", "build"]},
            "scripts": [{"name": "run_pipeline.py", "entry": "python scripts/run_pipeline.py"}],
        }
        return {"answer": json.dumps(answer, ensure_ascii=False), "request": {}, "raw": {}}

    monkeypatch.setattr(agent, "_run_workpackage_blueprint_query", _fake_blueprint_query)

    result = agent.converse("创建工作包 trace-case-v1.0.0", session_id="trace-session-002")

    traces = result.get("nanobot_traces") or {}
    opencode_logs = traces.get("nanobot_opencode") or []
    assert len(opencode_logs) >= 2
    assert str(opencode_logs[0].get("direction") or "") == "nanobot->opencode"
    assert str(opencode_logs[1].get("direction") or "") == "opencode->nanobot"

    memory = result.get("memory_objects") or {}
    assert isinstance(memory, dict)
    attempts = memory.get("blueprint_attempts") or []
    assert isinstance(attempts, list) and attempts
    assert str((attempts[0] or {}).get("stage") or "") == "BLUEPRINT_LOOP"
    opencode_ticket = memory.get("opencode_task_ticket") or {}
    assert str(opencode_ticket.get("phase") or "") == "BUILD_WITH_OPENCODE"
    artifacts = memory.get("build_artifacts_index") or {}
    assert str(artifacts.get("bundle_name") or "").startswith("trace-case-v1.0.0")
