from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from packages.factory_agent.agent import FactoryAgent
from services.governance_api.app.main import app


def test_runtime_pipeline_observable_from_factory_agent_publish(monkeypatch) -> None:
    agent = FactoryAgent()

    class _StubPublishWorkflow:
        @staticmethod
        def run(_prompt: str):
            return {"status": "ok", "runtime": {"status": "published", "receipt_id": "receipt_real_chain"}}

    monkeypatch.setattr(agent, "_publish_workflow", _StubPublishWorkflow())
    monkeypatch.setattr(
        agent,
        "_collect_workpackage_metadata",
        lambda _bundle_name: {
            "version": "v9.9.9",
            "checksum": "realchainchecksum",
            "skills_count": 3,
            "artifact_count": 7,
        },
    )

    result = agent._handle_publish_workpackage("发布 realchain-v9.9.9 到 runtime")
    assert result["status"] == "ok"

    client = TestClient(app)
    resp = client.get("/v1/governance/observability/runtime/workpackage-pipeline?window=24h")
    assert resp.status_code == 200
    payload = resp.json()
    rows = payload.get("items") or []
    target = next((row for row in rows if str(row.get("workpackage_id") or "") == "realchain-v9.9.9"), None)
    assert target is not None
    assert str(target.get("submit_status") or "") == "published"
    assert str(target.get("runtime_receipt_id") or "") == "receipt_real_chain"


def test_runtime_llm_interactions_observable_from_factory_agent_confirmation(monkeypatch) -> None:
    agent = FactoryAgent()
    monkeypatch.setattr(
        agent,
        "_run_requirement_query",
        lambda _prompt: {
            "answer": '{"target":"地址治理","data_sources":["gaode"],"outputs":["workpackage"]}',
            "latency_ms": 188,
            "token_usage": {"prompt": 20, "completion": 16, "total": 36},
        },
    )
    out = agent._handle_requirement_confirmation("请确认 llmchain-v1.0.0 的治理需求")
    assert out["status"] == "ok"

    client = TestClient(app)
    llm_resp = client.get("/v1/governance/observability/runtime/llm-interactions?window=24h")
    assert llm_resp.status_code == 200
    llm_payload = llm_resp.json()
    assert int(llm_payload.get("request_count") or 0) >= 1
    samples = llm_payload.get("samples") or []
    assert isinstance(samples, list)
    assert samples

