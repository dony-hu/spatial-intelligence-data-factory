from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_runtime_task(
    task_id: str,
    raw_id: str,
    raw_text: str,
    confidence: float,
    strategy: str = "auto_accept",
    batch_size: int = 1,
) -> None:
    REPOSITORY.create_task(
        task_id=task_id,
        batch_name="runtime-observability-contract",
        ruleset_id="default",
        status="SUCCEEDED",
        queue_backend="sync",
        queue_message="seeded",
        trace_id=f"trace_{task_id}",
    )
    results = []
    raw_records = []
    safe_batch_size = max(1, int(batch_size))
    for idx in range(safe_batch_size):
        record_id = f"{raw_id}-{idx:02d}"
        record_text = f"{raw_text}{idx + 1}号"
        results.append(
            {
                "raw_id": record_id,
                "canon_text": record_text,
                "confidence": confidence,
                "strategy": strategy,
                "evidence": {"items": [{"kind": "seed"}]},
            }
        )
        raw_records.append({"raw_id": record_id, "raw_text": record_text})
    REPOSITORY.save_results(task_id=task_id, results=results, raw_records=raw_records)
    REPOSITORY.record_observation_event(
        source_service="governance_worker",
        event_type="task_succeeded",
        status="success",
        trace_id=f"trace_{task_id}",
        task_id=task_id,
        payload={"stage": "seed"},
    )
    REPOSITORY.log_audit_event(
        event_type="task_seeded",
        caller="test",
        payload={"task_id": task_id, "reason": "contract_seed"},
    )


def test_runtime_summary_api_contract() -> None:
    client = TestClient(app)
    _seed_runtime_task("task_runtime_summary_001", "runtime-summary-r1", "上海市徐汇区肇嘉浜路111号", 0.91)

    resp = client.get("/v1/governance/observability/runtime/summary?window=24h")
    assert resp.status_code == 200
    payload = resp.json()
    assert "total_tasks" in payload
    assert "status_counts" in payload
    assert "avg_confidence" in payload
    assert "pending_review_tasks" in payload
    assert "reviewed_tasks" in payload
    assert "latest_task_at" in payload


def test_runtime_risk_distribution_api_contract() -> None:
    client = TestClient(app)
    _seed_runtime_task("task_runtime_risk_001", "runtime-risk-r1", "北京市朝阳区建国路88号", 0.45, strategy="human_required")

    resp = client.get("/v1/governance/observability/runtime/risk-distribution?window=24h")
    assert resp.status_code == 200
    payload = resp.json()
    assert "confidence_buckets" in payload
    assert "blocked_reason_top" in payload
    assert "low_confidence_pattern_top" in payload


def test_runtime_version_compare_api_contract() -> None:
    client = TestClient(app)
    resp = client.get(
        "/v1/governance/observability/runtime/version-compare"
        "?baseline=wp-address-topology-v1.0.1&candidate=wp-address-topology-v1.0.2"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "success_rate_delta" in payload
    assert "blocked_rate_delta" in payload
    assert "avg_confidence_delta" in payload


def test_runtime_tasks_api_contract() -> None:
    client = TestClient(app)
    _seed_runtime_task("task_runtime_tasks_001", "runtime-tasks-r1", "广州市天河区体育西路100号", 0.88, batch_size=4)

    resp = client.get("/v1/governance/observability/runtime/tasks?window=24h&status=SUCCEEDED&limit=20")
    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert "page" in payload
    assert "limit" in payload
    assert "total" in payload
    if payload["items"]:
        item = payload["items"][0]
        for key in ("task_id", "status", "ruleset_id", "confidence", "strategy", "review_status", "updated_at", "batch_size"):
            assert key in item
        assert any(int(row.get("batch_size") or 0) >= 1 for row in payload["items"])


def test_runtime_seed_demo_api_contract() -> None:
    client = TestClient(app)
    resp = client.post("/v1/governance/observability/runtime/seed-demo?total=120")
    assert resp.status_code == 200
    payload = resp.json()
    assert int(payload.get("total_seeded") or 0) == 120
    assert "status_counts" in payload
    assert int((payload.get("status_counts") or {}).get("SUCCEEDED", 0)) > 0


def test_runtime_task_detail_api_contract() -> None:
    client = TestClient(app)
    task_id = "task_runtime_detail_001"
    _seed_runtime_task(task_id, "runtime-detail-r1", "杭州市西湖区文三路478号", 0.87, batch_size=3)
    resp = client.get(f"/v1/governance/observability/runtime/tasks/{task_id}/detail")
    assert resp.status_code == 200
    payload = resp.json()
    assert "task" in payload
    assert "source_data" in payload
    assert "governance_results" in payload
    assert "process_logs" in payload
    assert isinstance(payload.get("source_data"), list)
    assert len(payload.get("source_data") or []) >= 3
    assert isinstance(payload.get("governance_results"), list)
    assert len(payload.get("governance_results") or []) >= 3
    assert isinstance((payload.get("process_logs") or {}).get("observation_events", []), list)
    assert isinstance((payload.get("process_logs") or {}).get("audit_events", []), list)
