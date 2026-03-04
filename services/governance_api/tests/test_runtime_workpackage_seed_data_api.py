from __future__ import annotations

import os

from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = str(os.getenv("DATABASE_URL") or "").strip()
if not os.environ["DATABASE_URL"]:
    raise RuntimeError("DATABASE_URL is required (docker pg); no local fallback is allowed")

from services.governance_api.app.main import app


def test_runtime_workpackage_seed_data_api() -> None:
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/workpackages/seed-crud-demo",
        params={"total": 12, "prefix": "wp_seed_crud"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("code") == "OK"
    data = payload.get("data") or {}
    items = data.get("items") or []
    assert len(items) >= 12
    statuses = {str(x.get("status") or "") for x in items if isinstance(x, dict)}
    assert {"created", "submitted", "packaged", "published", "blocked", "deleted"}.issubset(statuses)
    versions = {str(x.get("version") or "") for x in items if isinstance(x, dict)}
    assert len(versions) >= 3
