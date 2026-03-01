from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")
os.environ["OBSERVABILITY_ADMIN_TOKEN"] = os.getenv("OBSERVABILITY_ADMIN_TOKEN", "admin-token")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_llm_samples(workpackage_id: str, version: str) -> None:
    REPOSITORY.record_observation_event(
        source_service="llm",
        event_type="llm_request",
        status="success",
        trace_id=f"trace_rbac_{workpackage_id}",
        span_id="span_rbac_01",
        workpackage_id=workpackage_id,
        payload={
            "version": version,
            "model": "doubao-seed-2-0-pro-260215",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "latency_ms": 150,
            "token_usage": {"prompt": 30, "completion": 20, "total": 50},
            "prompt": "北京市朝阳区建国路88号",
            "response": "北京市朝阳区建国路88号",
        },
    )


def test_runtime_llm_interactions_viewer_masked_and_admin_full() -> None:
    client = TestClient(app)
    workpackage_id = "wp_obs_rbac_001"
    version = "v1.0.9"
    _seed_llm_samples(workpackage_id, version)

    viewer_resp = client.get(
        "/v1/governance/observability/runtime/llm-interactions"
        f"?window=24h&workpackage_id={workpackage_id}&version={version}&role=viewer"
    )
    assert viewer_resp.status_code == 200
    viewer_payload = viewer_resp.json()
    viewer_samples = viewer_payload.get("samples") or []
    assert viewer_samples
    viewer_prompt = str((viewer_samples[0] or {}).get("prompt") or "")
    assert "***" in viewer_prompt

    admin_resp = client.get(
        "/v1/governance/observability/runtime/llm-interactions"
        f"?window=24h&workpackage_id={workpackage_id}&version={version}&role=admin&actor=qa_admin",
        headers={"x-observability-token": os.environ["OBSERVABILITY_ADMIN_TOKEN"]},
    )
    assert admin_resp.status_code == 200
    admin_payload = admin_resp.json()
    admin_samples = admin_payload.get("samples") or []
    assert admin_samples
    admin_prompt = str((admin_samples[0] or {}).get("prompt") or "")
    assert "北京市朝阳区建国路88号" in admin_prompt

