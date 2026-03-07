from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = os.getenv(
    "DATABASE_URL",
    "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory",
)

from services.governance_api.app.main import app
from services.governance_api.app.routers import observability


def test_runtime_preflight_llm_probe_uses_factory_agent_nanobot_chain(monkeypatch) -> None:
    calls: list[dict] = []

    class _FakeAgent:
        def converse(self, message: str, session_id: str | None = None):
            calls.append({"message": message, "session_id": session_id})
            return {"status": "ok", "action": "preflight_probe", "message": "OK"}

    monkeypatch.setattr(observability, "_FACTORY_AGENT", _FakeAgent())
    monkeypatch.setattr(
        observability.GOVERNANCE_SERVICE,
        "runtime_summary",
        lambda **_kwargs: {"total_tasks": 0},
    )

    class _Proc:
        returncode = 0
        stdout = "opencode 1.0.0"
        stderr = ""

    monkeypatch.setattr(observability.subprocess, "run", lambda *args, **kwargs: _Proc())

    client = TestClient(app)
    resp = client.get(
        "/v1/governance/observability/runtime/preflight"
        "?verify_llm=true&fail_fast=false&llm_retries=1"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("checks", {}).get("llm", {}).get("ok") is True
    assert calls, json.dumps(payload, ensure_ascii=False)
    assert "OK" in str(payload.get("checks", {}).get("llm", {}).get("detail") or "")


def test_runtime_preflight_marks_blocked_when_agent_returns_llm_blocked(monkeypatch) -> None:
    class _BlockedAgent:
        def converse(self, message: str, session_id: str | None = None):
            return {
                "status": "blocked",
                "action": "general_governance_chat",
                "llm_status": "blocked",
                "message": "LLM 对话阻塞，请稍后重试或改为明确的数据治理问题。",
            }

    monkeypatch.setattr(observability, "_FACTORY_AGENT", _BlockedAgent())
    monkeypatch.setattr(
        observability.GOVERNANCE_SERVICE,
        "runtime_summary",
        lambda **_kwargs: {"total_tasks": 0},
    )

    class _Proc:
        returncode = 0
        stdout = "opencode 1.0.0"
        stderr = ""

    monkeypatch.setattr(observability.subprocess, "run", lambda *args, **kwargs: _Proc())

    client = TestClient(app)
    resp = client.get(
        "/v1/governance/observability/runtime/preflight"
        "?verify_llm=true&fail_fast=false&llm_retries=1"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("status") == "blocked"
    assert payload.get("checks", {}).get("llm", {}).get("ok") is False
    assert any(str(x).startswith("llm:") for x in (payload.get("errors") or []))
