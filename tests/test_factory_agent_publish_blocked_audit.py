from __future__ import annotations

import os

os.environ.setdefault("GOVERNANCE_ALLOW_MEMORY_FALLBACK", "1")

from packages.factory_agent.agent import FactoryAgent
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def test_publish_blocked_should_log_blocked_confirmation_audit(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = len(REPOSITORY.list_audit_events())
    agent = FactoryAgent()
    result = agent.converse("发布 missing-demo-v9.9.9 到 runtime")
    assert result["status"] == "blocked"

    after_events = REPOSITORY.list_audit_events()
    assert len(after_events) >= before + 1
    latest = after_events[-1]
    assert latest["event_type"] == "workpackage_publish_blocked"
    payload = latest.get("payload") or {}
    assert payload.get("reason")
    assert payload.get("confirmation_user")
    assert payload.get("confirmation_decision")
    assert payload.get("confirmation_timestamp")
