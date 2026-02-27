from __future__ import annotations

import os

os.environ.setdefault("GOVERNANCE_ALLOW_MEMORY_FALLBACK", "1")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def test_observability_events_and_trace_replay_contract() -> None:
    trace_id = "trace_obs_foundation_001"
    REPOSITORY.record_observation_event(
        source_service="governance_api",
        event_type="task_submitted",
        status="success",
        trace_id=trace_id,
        task_id="task_obs_001",
        payload={"stage": "submit"},
    )
    REPOSITORY.record_observation_event(
        source_service="governance_worker",
        event_type="task_succeeded",
        status="success",
        trace_id=trace_id,
        task_id="task_obs_001",
        payload={"stage": "finish"},
    )

    client = TestClient(app)
    events_resp = client.get(f"/v1/governance/observability/events?trace_id={trace_id}&limit=10")
    assert events_resp.status_code == 200
    events_payload = events_resp.json()
    assert events_payload["total"] >= 2
    assert all(item["trace_id"] == trace_id for item in events_payload["items"])

    replay_resp = client.get(f"/v1/governance/observability/traces/{trace_id}/replay")
    assert replay_resp.status_code == 200
    replay_payload = replay_resp.json()
    assert replay_payload["trace_id"] == trace_id
    assert replay_payload["total"] >= 2
    assert replay_payload["timeline"][0]["event_type"] == "task_submitted"


def test_observability_snapshot_timeseries_and_alert_ack_contract() -> None:
    REPOSITORY.upsert_observation_metric(
        metric_name="task.success_rate",
        metric_value=0.98,
        labels={"env": "dev", "owner_line": "address"},
        window_start="2026-02-27T13:00:00Z",
        window_end="2026-02-27T13:05:00Z",
    )
    created = REPOSITORY.create_observation_alert(
        alert_rule="blocked_rate_high",
        severity="error",
        trigger_value=0.21,
        threshold_value=0.15,
        trace_id="trace_alert_001",
    )

    client = TestClient(app)
    snapshot_resp = client.get("/v1/governance/observability/snapshot?env=dev")
    assert snapshot_resp.status_code == 200
    snapshot_payload = snapshot_resp.json()
    assert "kpis" in snapshot_payload
    assert "alerts" in snapshot_payload

    series_resp = client.get("/v1/governance/observability/timeseries?metric_name=task.success_rate&limit=10")
    assert series_resp.status_code == 200
    series_payload = series_resp.json()
    assert series_payload["metric_name"] == "task.success_rate"
    assert series_payload["total"] >= 1

    list_alerts = client.get("/v1/governance/observability/alerts?status=open")
    assert list_alerts.status_code == 200
    list_payload = list_alerts.json()
    assert list_payload["total"] >= 1

    ack_resp = client.post(f"/v1/governance/observability/alerts/{created['alert_id']}/ack", json={"actor": "owner_a"})
    assert ack_resp.status_code == 200
    ack_payload = ack_resp.json()
    assert ack_payload["status"] == "acked"
