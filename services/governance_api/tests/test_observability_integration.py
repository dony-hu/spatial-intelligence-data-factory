from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_worker.app.core.queue import run_in_memory_all


def test_observability_snapshot_reflects_task_lifecycle() -> None:
    client = TestClient(app)

    submit = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-observe-integ-001",
            "batch_name": "batch-observe-integ",
            "ruleset_id": "default",
            "records": [{"raw_id": "obs-integ-r1", "raw_text": "上海市徐汇区肇嘉浜路111号"}],
        },
    )
    assert submit.status_code == 200
    task_id = submit.json()["task_id"]

    processed = run_in_memory_all()
    assert processed >= 1

    review = client.post(
        f"/v1/governance/reviews/{task_id}/decision",
        json={"raw_id": "obs-integ-r1", "review_status": "approved", "reviewer": "obs-integ"},
    )
    assert review.status_code == 200

    snapshot = client.get("/v1/governance/lab/observability/snapshot?env=dev")
    assert snapshot.status_code == 200
    data = snapshot.json()

    assert data["environment"] == "dev"
    assert data["l1"]["total_tasks"] >= 1
    assert 0.0 <= float(data["l1"]["success_rate"]) <= 1.0
    assert data["l2"]["active_ruleset_id"]
    assert "coverage_status" in data["l3"]
    assert isinstance(data.get("alerts", []), list)
    assert "address_line" in data

    status_counts = data["l3"].get("status_counts", {})
    assert status_counts.get("REVIEWED", 0) >= 1
    address_line = data["address_line"]
    assert isinstance(address_line.get("task_status", {}), dict)
    assert isinstance(address_line.get("quality_score", 0), (int, float))
    assert isinstance(address_line.get("failure_replay_refs", []), list)
    assert isinstance(address_line.get("sample_trace_links", []), list)


def test_observability_snapshot_includes_recent_audit_events() -> None:
    client = TestClient(app)

    put_ruleset = client.put(
        "/v1/governance/rulesets/obs-integ-rs-1",
        json={
            "version": "v1",
            "is_active": False,
            "config_json": {"thresholds": {"t_high": 0.8, "t_low": 0.6}},
        },
    )
    assert put_ruleset.status_code == 200

    publish = client.post(
        "/v1/governance/rulesets/obs-integ-rs-1/publish",
        json={"operator": "obs-integ", "reason": "integration test publish"},
    )
    assert publish.status_code == 409
    assert publish.json()["detail"]["code"] == "APPROVAL_GATE_REQUIRED"

    snapshot = client.get("/v1/governance/lab/observability/snapshot?include_events=true")
    assert snapshot.status_code == 200
    data = snapshot.json()

    events = data.get("events", [])
    assert isinstance(events, list)
    assert len(events) >= 1
    assert any(
        evt.get("event_type")
        in {"ruleset_published", "ruleset_activated", "approval_changed", "ruleset_publish_blocked"}
        for evt in events
    )


def test_observability_stream_emits_connected_and_snapshot_events() -> None:
    client = TestClient(app)

    response = client.get("/v1/governance/lab/observability/stream?env=staging&interval_sec=1&max_events=2")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    body = response.text
    assert "event: connected" in body
    assert "event: snapshot" in body
    assert '"environment": "staging"' in body
