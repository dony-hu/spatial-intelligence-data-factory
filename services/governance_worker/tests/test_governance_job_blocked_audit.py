from __future__ import annotations

import os


from services.governance_worker.app.jobs import governance_job


def test_governance_job_marks_blocked_and_logs_audit(monkeypatch) -> None:
    events: list[tuple[str, str, dict]] = []
    status_updates: list[str] = []

    monkeypatch.setattr(governance_job, "ingest_run", lambda payload: payload)
    monkeypatch.setattr(
        governance_job,
        "run_address_pipeline",
        lambda _records, _ruleset: (_ for _ in ()).throw(RuntimeError("blocked: pipeline input invalid")),
    )
    monkeypatch.setattr(governance_job.REPOSITORY, "set_task_status", lambda _task_id, status: status_updates.append(status))
    monkeypatch.setattr(
        governance_job.REPOSITORY,
        "log_blocked_confirmation",
        lambda event_type, caller, payload, related_change_id=None: events.append((event_type, caller, payload)) or {"event_id": "evt_ut"},
    )

    result = governance_job.run(
        {"task_id": "t-blocked-audit", "ruleset_id": "default", "records": [{"raw_id": "r1", "raw_text": " "}]}  # noqa: E501
    )
    assert result["status"] == "BLOCKED"
    assert result["block_reason"] == "pipeline input invalid"
    assert "RUNNING" in status_updates
    assert "BLOCKED" in status_updates
    assert events, "expected blocked audit event"
    assert events[0][0] == "governance_job_blocked"
    assert events[0][2]["reason"] == "pipeline input invalid"
