from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app


def test_runtime_seed_workpackage_demo_api_contract() -> None:
    client = TestClient(app)
    resp = client.post("/v1/governance/observability/runtime/seed-workpackage-demo?total=12")
    assert resp.status_code == 200
    payload = resp.json()
    assert int(payload.get("total_seeded") or 0) == 12
    assert "stage_counts" in payload
    assert int((payload.get("stage_counts") or {}).get("finished", 0)) >= 1

    pipeline_resp = client.get("/v1/governance/observability/runtime/workpackage-pipeline?window=24h")
    assert pipeline_resp.status_code == 200
    pipeline = pipeline_resp.json()
    assert int(pipeline.get("total_workpackages") or 0) >= 1
    assert isinstance(pipeline.get("items"), list)

