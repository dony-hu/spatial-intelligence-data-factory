from __future__ import annotations

import os

os.environ.setdefault("GOVERNANCE_ALLOW_MEMORY_FALLBACK", "1")

from services.governance_worker.app.jobs import governance_job


class _DummyRuntime:
    def run_task(self, task_context: dict, ruleset: dict):
        assert os.getenv("OPENHANDS_STRICT") == "1"
        return _DummyResult()


class _DummyResult:
    def model_dump(self) -> dict:
        return {"strategy": "auto_accept", "confidence": 0.9, "evidence": {"items": []}}


def test_governance_job_sets_strict_mode_by_default(monkeypatch) -> None:
    monkeypatch.delenv("OPENHANDS_STRICT", raising=False)
    monkeypatch.setattr(governance_job, "ingest_run", lambda payload: payload)
    monkeypatch.setattr(governance_job, "run_address_pipeline", lambda records, _ruleset: [])
    monkeypatch.setattr(governance_job, "get_runtime", lambda: _DummyRuntime())
    monkeypatch.setattr(governance_job, "persist_results", lambda *_args, **_kwargs: {"status": "SUCCEEDED"})
    monkeypatch.setattr(governance_job.REPOSITORY, "set_task_status", lambda *_args, **_kwargs: None)

    result = governance_job.run({"task_id": "t-strict-default", "records": [], "ruleset_id": "default"})
    assert result["status"] == "SUCCEEDED"
    assert os.getenv("OPENHANDS_STRICT") is None
