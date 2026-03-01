from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_latency_data() -> None:
    for idx in range(3):
        task_id = f"task_latency_{idx:02d}"
        REPOSITORY.create_task(
            task_id=task_id,
            batch_name="runtime-latency-seed",
            ruleset_id="default",
            status="SUCCEEDED",
            queue_backend="sync",
            queue_message="seeded",
            trace_id=f"trace_latency_{idx:02d}",
        )
        REPOSITORY.record_observation_event(
            source_service="governance_worker",
            event_type="task_finished",
            status="success",
            trace_id=f"trace_latency_{idx:02d}",
            task_id=task_id,
            payload={"duration_ms": 2000 + idx * 500},
        )


def test_runtime_freshness_latency_summary_contract() -> None:
    client = TestClient(app)
    _seed_latency_data()
    resp = client.get("/v1/governance/observability/runtime/freshness-latency/summary?window=24h")
    assert resp.status_code == 200
    payload = resp.json()
    assert "metrics" in payload
    assert "thresholds" in payload
    assert "violations" in payload
    assert "bottleneck_layer" in payload
    metrics = payload["metrics"]
    assert "event_lag_seconds" in metrics
    assert "aggregation_lag_seconds" in metrics
    assert "dashboard_data_age_seconds" in metrics


def test_runtime_freshness_latency_evaluate_contract() -> None:
    client = TestClient(app)
    _seed_latency_data()
    resp = client.post("/v1/governance/observability/runtime/freshness-latency/evaluate?window=24h")
    assert resp.status_code == 200
    payload = resp.json()
    assert "triggered_alerts" in payload
    assert "triggered_count" in payload
    assert "violation_count" in payload
