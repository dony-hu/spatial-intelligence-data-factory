from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_llm_interactions(workpackage_id: str, version: str) -> None:
    trace_id = f"trace_llm_{workpackage_id}_{version}".replace(".", "_")
    REPOSITORY.record_observation_event(
        source_service="llm",
        event_type="llm_request",
        status="success",
        trace_id=trace_id,
        span_id="span_llm_req",
        workpackage_id=workpackage_id,
        payload={
            "pipeline_stage": "llm_confirmed",
            "version": version,
            "model": "doubao-seed-2-0-pro-260215",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "latency_ms": 420,
            "token_usage": {"prompt": 120, "completion": 80, "total": 200},
            "prompt": "请确认地址治理工作包需求。",
            "response": "已确认需求，进入打包阶段。",
        },
    )
    REPOSITORY.record_observation_event(
        source_service="llm",
        event_type="llm_response",
        status="error",
        trace_id=trace_id,
        span_id="span_llm_resp",
        workpackage_id=workpackage_id,
        payload={
            "pipeline_stage": "llm_confirmed",
            "version": version,
            "model": "doubao-seed-2-0-pro-260215",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "latency_ms": 680,
            "token_usage": {"prompt": 100, "completion": 0, "total": 100},
            "failure_reason": "rate_limit",
            "prompt": "再次确认需求。",
            "response": "请求受限。",
        },
    )


def test_runtime_llm_interactions_api_contract() -> None:
    client = TestClient(app)
    workpackage_id = "wp_obs_llm_001"
    version = "v2.0.0"
    _seed_llm_interactions(workpackage_id, version)

    resp = client.get(
        "/v1/governance/observability/runtime/llm-interactions"
        f"?window=24h&workpackage_id={workpackage_id}&version={version}"
    )
    assert resp.status_code == 200
    payload = resp.json()
    for key in (
        "model",
        "base_url",
        "request_count",
        "success_count",
        "failure_count",
        "latency_ms_p50",
        "latency_ms_p90",
        "token_usage",
        "failure_reasons_top",
        "samples",
    ):
        assert key in payload
    assert int(payload.get("request_count") or 0) >= 1

