from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_workpackage_pipeline(workpackage_id: str, version: str) -> None:
    trace_id = f"trace_{workpackage_id}_{version}".replace(".", "_")
    stages = [
        ("created", "factory_cli", "workpackage_created"),
        ("llm_confirmed", "factory_agent", "requirements_confirmed"),
        ("packaged", "factory_agent", "workpackage_packaged"),
        ("submitted", "governance_runtime", "runtime_submit_requested"),
        ("accepted", "governance_runtime", "runtime_submit_accepted"),
        ("running", "governance_runtime", "runtime_task_running"),
        ("finished", "governance_runtime", "runtime_task_finished"),
    ]
    for idx, (stage, source, event_type) in enumerate(stages):
        REPOSITORY.record_observation_event(
            source_service=source,
            event_type=event_type,
            status="success",
            trace_id=trace_id,
            span_id=f"span_{idx:02d}",
            workpackage_id=workpackage_id,
            payload={
                "pipeline_stage": stage,
                "client_type": "test_client",
                "version": version,
                "runtime_receipt_id": f"receipt_{workpackage_id}_{version}",
                "checksum": "abc123checksum",
                "skills_count": 4,
                "artifact_count": 12,
                "submit_status": "published",
                "latency_ms": 80 + idx * 20,
            },
        )


def test_runtime_workpackage_pipeline_api_contract() -> None:
    client = TestClient(app)
    _seed_workpackage_pipeline("wp_obs_pipeline_001", "v1.0.0")

    resp = client.get("/v1/governance/observability/runtime/workpackage-pipeline?window=24h&client_type=test_client")
    assert resp.status_code == 200
    payload = resp.json()
    assert "total_workpackages" in payload
    assert "stage_counts" in payload
    assert "end_to_end_success_rate" in payload
    assert "latency_breakdown_ms_p50_p90" in payload
    assert "runtime_submit_success_rate" in payload
    assert int(payload.get("total_workpackages") or 0) >= 1
    items = payload.get("items") or []
    assert items
    first = items[0]
    for key in ("checksum", "skills_count", "artifact_count", "submit_status"):
        assert key in first
