from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_workpackage_events(workpackage_id: str, version: str) -> None:
    trace_id = f"trace_evt_{workpackage_id}_{version}".replace(".", "_")
    REPOSITORY.record_observation_event(
        source_service="factory_cli",
        event_type="workpackage_created",
        status="success",
        trace_id=trace_id,
        span_id="span_root",
        workpackage_id=workpackage_id,
        payload={
            "pipeline_stage": "created",
            "client_type": "user",
            "version": version,
        },
    )
    REPOSITORY.record_observation_event(
        source_service="llm",
        event_type="llm_response",
        status="success",
        trace_id=trace_id,
        span_id="span_llm",
        workpackage_id=workpackage_id,
        payload={
            "pipeline_stage": "llm_confirmed",
            "parent_span_id": "span_root",
            "client_type": "user",
            "version": version,
            "model": "doubao-seed-2-0-pro-260215",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        },
    )


def test_runtime_workpackage_events_api_contract() -> None:
    client = TestClient(app)
    workpackage_id = "wp_obs_events_001"
    version = "v1.2.3"
    _seed_workpackage_events(workpackage_id, version)

    resp = client.get(
        "/v1/governance/observability/runtime/workpackage-events"
        f"?workpackage_id={workpackage_id}&version={version}&window=24h"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "total" in payload
    assert "items" in payload
    items = payload.get("items") or []
    assert isinstance(items, list)
    assert len(items) >= 1
    row = items[0]
    for key in ("trace_id", "span_id", "parent_span_id", "source", "event_type", "occurred_at", "status", "payload_summary"):
        assert key in row

