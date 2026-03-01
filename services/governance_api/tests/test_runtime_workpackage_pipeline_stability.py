from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app


def test_runtime_workpackage_pipeline_multi_batch_stability() -> None:
    client = TestClient(app)
    resp = client.post("/v1/governance/observability/runtime/seed-workpackage-demo?total=80")
    assert resp.status_code == 200
    payload = resp.json()
    assert int(payload.get("total_seeded") or 0) == 80

    pipeline_resp = client.get("/v1/governance/observability/runtime/workpackage-pipeline?window=24h")
    assert pipeline_resp.status_code == 200
    pipeline = pipeline_resp.json()
    assert int(pipeline.get("total_workpackages") or 0) >= 80
    stage_counts = pipeline.get("stage_counts") or {}
    assert int(stage_counts.get("created") or 0) >= 80
    assert int(stage_counts.get("finished") or 0) >= 80
    assert float(pipeline.get("runtime_submit_success_rate") or 0.0) >= 0.99
    items = pipeline.get("items") or []
    assert items
    first = items[0]
    for key in ("runtime_receipt_id", "submit_status", "checksum", "skills_count", "artifact_count"):
        assert key in first

