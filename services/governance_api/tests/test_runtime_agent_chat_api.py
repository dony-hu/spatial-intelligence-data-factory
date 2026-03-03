from __future__ import annotations

import os
import json

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

import pytest
from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.routers import observability


def test_runtime_agent_chat_api_returns_agent_response() -> None:
    class _FakeAgent:
        def converse(self, _message: str, session_id: str | None = None):
            return {"status": "ok", "action": "list_workpackages", "message": "已发布 0 个工作包"}

    observability._FACTORY_AGENT = _FakeAgent()
    observability.GOVERNANCE_SERVICE.log_audit_event = lambda **_kwargs: None
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/agent-chat",
        json={
            "session_id": "s2-15-manual-001",
            "message": "列出工作包",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "session_id" in payload
    assert "result" in payload
    result = payload.get("result") or {}
    assert isinstance(result, dict)
    assert "status" in result
    assert "action" in result


def test_runtime_agent_chat_api_exposes_raw_llm_payload_real_call() -> None:
    if os.getenv("RUN_REAL_LLM_GATE") != "1":
        pytest.skip("set RUN_REAL_LLM_GATE=1 to run real external LLM call")
    if not os.getenv("LLM_API_KEY"):
        pytest.skip("LLM_API_KEY is required for real external LLM call")

    observability._FACTORY_AGENT = None
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/agent-chat",
        json={
            "session_id": "s2-15-manual-raw-001",
            "message": "这是一个未匹配其它意图的需求确认请求",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    llm_raw_text = str(payload.get("result", {}).get("llm_raw_text") or "")
    llm_raw_response = payload.get("result", {}).get("llm_raw_response") or {}
    llm_request = payload.get("result", {}).get("llm_request") or {}
    assert llm_raw_text
    assert isinstance(llm_raw_response, dict)
    assert isinstance(llm_raw_response.get("choices"), list)
    assert isinstance(llm_request, dict)
    assert isinstance(llm_request.get("messages"), list)


def test_runtime_agent_chat_api_returns_blueprint_summary_fields(monkeypatch) -> None:
    class _FakeAgent:
        def converse(self, _message: str):
            return {
                "status": "ok",
                "action": "generate_workpackage",
                "bundle_name": "ctx-e2e-v1.0.0",
                "schema_fix_rounds": [{"round": 1, "errors": ["io_contract.input_schema must be object"]}],
                "workpackage_blueprint_summary": {
                    "name": "ctx-e2e",
                    "version": "v1.0.0",
                    "api_count": 1,
                    "script_count": 1,
                },
            }

    observability._FACTORY_AGENT = _FakeAgent()
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/agent-chat",
        json={"session_id": "runtime-s2-15-summary-001", "message": "创建工作包"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload.get("schema_fix_rounds"), list)
    assert isinstance(payload.get("workpackage_blueprint_summary"), dict)
    assert (payload.get("workpackage_blueprint_summary") or {}).get("name") == "ctx-e2e"


def test_runtime_agent_chat_api_returns_nanobot_trace_streams(monkeypatch) -> None:
    monkeypatch.setattr(observability.GOVERNANCE_SERVICE, "log_audit_event", lambda **_kwargs: None)

    class _FakeAgent:
        def converse(self, _message: str):
            return {
                "status": "ok",
                "action": "generate_workpackage",
                "bundle_name": "ctx-e2e-v1.0.0",
                "bundle_path": "workpackages/bundles/ctx-e2e-v1.0.0",
                "message": "工作包 ctx-e2e-v1.0.0 已生成",
                "nanobot_traces": {
                    "client_nanobot": [
                        {
                            "session_id": "runtime-trace-001",
                            "trace_id": "trace_a",
                            "channel": "client_nanobot",
                            "direction": "client->nanobot",
                            "stage": "conversation",
                            "event_type": "message",
                            "content_text": "创建工作包并生成脚本",
                            "content_json": {"message": "创建工作包并生成脚本"},
                            "artifacts": [],
                            "status": "success",
                            "ts": "2026-03-03T10:00:00+00:00",
                        },
                        {
                            "session_id": "runtime-trace-001",
                            "trace_id": "trace_a",
                            "channel": "client_nanobot",
                            "direction": "nanobot->client",
                            "stage": "generate_workpackage",
                            "event_type": "message",
                            "content_text": "工作包 ctx-e2e-v1.0.0 已生成",
                            "content_json": {"status": "ok"},
                            "artifacts": [],
                            "status": "ok",
                            "ts": "2026-03-03T10:00:01+00:00",
                        },
                    ],
                    "nanobot_opencode": [
                        {
                            "session_id": "runtime-trace-001",
                            "trace_id": "trace_a",
                            "channel": "nanobot_opencode",
                            "direction": "nanobot->opencode",
                            "stage": "bundle_build",
                            "event_type": "task_start",
                            "content_text": "开始构建",
                            "content_json": {"bundle_name": "ctx-e2e-v1.0.0"},
                            "artifacts": [],
                            "status": "success",
                            "ts": "2026-03-03T10:00:02+00:00",
                        },
                        {
                            "session_id": "runtime-trace-001",
                            "trace_id": "trace_a",
                            "channel": "nanobot_opencode",
                            "direction": "opencode->nanobot",
                            "stage": "bundle_build",
                            "event_type": "task_finish",
                            "content_text": "构建完成",
                            "content_json": {"bundle_name": "ctx-e2e-v1.0.0"},
                            "artifacts": ["workpackages/bundles/ctx-e2e-v1.0.0/workpackage.json"],
                            "status": "success",
                            "ts": "2026-03-03T10:00:03+00:00",
                        },
                    ],
                },
                "workpackage_blueprint_summary": {
                    "name": "ctx-e2e",
                    "version": "v1.0.0",
                    "script_count": 2,
                },
            }

    observability._FACTORY_AGENT = _FakeAgent()
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/agent-chat",
        json={"session_id": "runtime-trace-001", "message": "创建工作包并生成脚本"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    traces = payload.get("nanobot_traces") or {}
    assert isinstance(traces, dict)
    client_logs = traces.get("client_nanobot") or []
    opencode_logs = traces.get("nanobot_opencode") or []
    assert isinstance(client_logs, list) and len(client_logs) >= 2
    assert isinstance(opencode_logs, list) and len(opencode_logs) >= 2
    assert str(client_logs[0].get("direction") or "") in {"client->nanobot", "nanobot->client"}
    assert str(opencode_logs[0].get("direction") or "") in {"nanobot->opencode", "opencode->nanobot"}


def test_runtime_agent_chat_api_passthroughs_agent_trace_payload_without_router_fabrication(monkeypatch) -> None:
    monkeypatch.setattr(observability.GOVERNANCE_SERVICE, "log_audit_event", lambda **_kwargs: None)

    expected_traces = {
        "client_nanobot": [
            {
                "session_id": "runtime-trace-pass-001",
                "trace_id": "trace_x",
                "channel": "client_nanobot",
                "direction": "client->nanobot",
                "stage": "conversation",
                "event_type": "message",
                "content_text": "创建工作包",
                "content_json": {"message": "创建工作包"},
                "artifacts": [],
                "status": "success",
                "ts": "2026-03-03T10:00:00+00:00",
            }
        ],
        "nanobot_opencode": [
            {
                "session_id": "runtime-trace-pass-001",
                "trace_id": "trace_x",
                "channel": "nanobot_opencode",
                "direction": "nanobot->opencode",
                "stage": "bundle_build",
                "event_type": "task_start",
                "content_text": "开始构建",
                "content_json": {"bundle_name": "ctx-e2e-v1.0.0"},
                "artifacts": ["workpackages/bundles/ctx-e2e-v1.0.0/workpackage.json"],
                "status": "success",
                "ts": "2026-03-03T10:00:01+00:00",
            }
        ],
    }

    class _FakeAgent:
        def converse(self, _message: str, session_id: str | None = None):
            return {
                "status": "ok",
                "action": "generate_workpackage",
                "bundle_name": "ctx-e2e-v1.0.0",
                "message": "工作包已生成",
                "nanobot_traces": expected_traces,
                "trace_log_path": "output/runtime_traces/runtime-trace-pass-001.jsonl",
            }

    observability._FACTORY_AGENT = _FakeAgent()
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/agent-chat",
        json={"session_id": "runtime-trace-pass-001", "message": "创建工作包"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("nanobot_traces") == expected_traces
    assert payload.get("trace_log_path") == "output/runtime_traces/runtime-trace-pass-001.jsonl"


def test_runtime_agent_chat_api_writes_runtime_api_trace_log(monkeypatch, tmp_path) -> None:
    trace_path = tmp_path / "runtime_api_trace.jsonl"
    monkeypatch.setenv("RUNTIME_API_TRACE_LOG", str(trace_path))
    monkeypatch.setattr(observability.GOVERNANCE_SERVICE, "log_audit_event", lambda **_kwargs: None)

    class _FakeAgent:
        def converse(self, _message: str, session_id: str | None = None):
            return {
                "status": "ok",
                "action": "generate_workpackage",
                "bundle_name": "trace-case-v1.0.0",
                "message": "工作包 trace-case-v1.0.0 已生成",
                "nanobot_traces": {"client_nanobot": [], "nanobot_opencode": []},
            }

    observability._FACTORY_AGENT = _FakeAgent()
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/agent-chat",
        json={"session_id": "trace-log-s1", "message": "创建工作包并生成"},
    )
    assert resp.status_code == 200
    assert trace_path.exists()
    rows = [json.loads(x) for x in trace_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert any(str((row.get("event_type") or "")) == "runtime_agent_chat" for row in rows)
