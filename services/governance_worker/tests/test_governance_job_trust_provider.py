from __future__ import annotations

import os

os.environ.setdefault("GOVERNANCE_ALLOW_MEMORY_FALLBACK", "1")

from services.governance_worker.app.jobs import governance_job


class _DummyRuntime:
    def run_task(self, task_context: dict, ruleset: dict):
        return _DummyResult()


class _DummyResult:
    def model_dump(self) -> dict:
        return {"strategy": "auto_accept", "confidence": 0.9, "evidence": {"items": []}}


class _EnabledTrustProvider:
    def enabled(self) -> bool:
        return True

    def query_admin_division(self, namespace: str, name: str, parent_hint=None):
        return []

    def query_road(self, namespace: str, name: str, adcode_hint=None):
        return []

    def query_poi(self, namespace: str, name: str, adcode_hint=None, top_k: int = 5):
        return []


class _DisabledTrustProvider:
    def enabled(self) -> bool:
        return False


def test_governance_job_passes_trust_provider_when_ruleset_declares_trust(monkeypatch) -> None:
    captured: dict = {}

    def _fake_run(records, ruleset, trust_provider=None):
        captured["ruleset"] = ruleset
        captured["trust_provider"] = trust_provider
        return []

    monkeypatch.setattr(governance_job, "ingest_run", lambda payload: payload)
    monkeypatch.setattr(governance_job, "run_address_pipeline", _fake_run)
    monkeypatch.setattr(governance_job, "get_runtime", lambda: _DummyRuntime())
    monkeypatch.setattr(governance_job, "persist_results", lambda *_args, **_kwargs: {"status": "SUCCEEDED"})
    monkeypatch.setattr(
        governance_job.REPOSITORY,
        "get_ruleset",
        lambda _ruleset_id: {"ruleset_id": "default", "config_json": {"trust_namespace": "system.trust.dev"}},
    )
    monkeypatch.setattr(governance_job, "_new_trust_provider", lambda: _EnabledTrustProvider())
    monkeypatch.setattr(governance_job.REPOSITORY, "set_task_status", lambda *_args, **_kwargs: None)

    result = governance_job.run({"task_id": "t-trust-provider", "records": [{"raw_id": "r1", "raw_text": "深圳"}], "ruleset_id": "default"})
    assert result["status"] == "SUCCEEDED"
    assert captured["ruleset"]["trust_namespace"] == "system.trust.dev"
    assert captured["trust_provider"] is not None


def test_governance_job_blocks_when_trust_required_but_provider_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(governance_job, "ingest_run", lambda payload: payload)
    monkeypatch.setattr(governance_job, "run_address_pipeline", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(governance_job, "get_runtime", lambda: _DummyRuntime())
    monkeypatch.setattr(governance_job, "persist_results", lambda *_args, **_kwargs: {"status": "SUCCEEDED"})
    monkeypatch.setattr(
        governance_job.REPOSITORY,
        "get_ruleset",
        lambda _ruleset_id: {
            "ruleset_id": "default",
            "config_json": {"require_trust_enhancement": True, "trust_namespace": "system.trust.dev"},
        },
    )
    monkeypatch.setattr(governance_job, "_new_trust_provider", lambda: _DisabledTrustProvider())
    monkeypatch.setattr(governance_job.REPOSITORY, "set_task_status", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(governance_job.REPOSITORY, "log_blocked_confirmation", lambda *_args, **_kwargs: {"event_id": "evt-trust-blocked"})

    result = governance_job.run({"task_id": "t-trust-blocked", "records": [{"raw_id": "r1", "raw_text": "深圳"}], "ruleset_id": "default"})
    assert result["status"] == "BLOCKED"
    assert result["block_reason"] == "trust provider unavailable"
