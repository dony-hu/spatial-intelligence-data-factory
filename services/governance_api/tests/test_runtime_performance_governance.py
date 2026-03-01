from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_perf_data() -> None:
    task_id = "task_perf_001"
    REPOSITORY.create_task(
        task_id=task_id,
        batch_name="runtime-perf-seed",
        ruleset_id="default",
        status="SUCCEEDED",
        queue_backend="sync",
        queue_message="seeded",
        trace_id="trace_perf_001",
    )
    REPOSITORY.save_results(
        task_id=task_id,
        results=[
            {
                "raw_id": "raw_perf_001",
                "canon_text": "深圳市南山区科技园南区8栋",
                "confidence": 0.91,
                "strategy": "auto_accept",
                "evidence": {"items": [{"kind": "seed"}]},
            }
        ],
        raw_records=[{"raw_id": "raw_perf_001", "raw_text": "深圳市南山区科技园南区8栋"}],
    )


def test_runtime_performance_summary_contract() -> None:
    client = TestClient(app)
    _seed_perf_data()
    resp = client.get("/v1/governance/observability/runtime/performance/summary?window=24h")
    assert resp.status_code == 200
    payload = resp.json()
    assert "metrics" in payload
    assert "thresholds" in payload
    assert "violations" in payload
    assert "archive" in payload


def test_runtime_performance_evaluate_contract() -> None:
    client = TestClient(app)
    _seed_perf_data()
    resp = client.post(
        "/v1/governance/observability/runtime/performance/evaluate"
        "?window=24h&aggregate_threshold_ms=1&detail_threshold_ms=1"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "triggered_count" in payload
    assert "violation_count" in payload
    assert int(payload.get("violation_count") or 0) >= 1
