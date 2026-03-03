from __future__ import annotations

import os
import json
from uuid import uuid4

from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = str(os.getenv("DATABASE_URL") or "").strip()
if not os.environ["DATABASE_URL"]:
    raise RuntimeError("DATABASE_URL is required (docker pg); no local fallback is allowed")

from services.governance_api.app.main import app


def test_runtime_workpackage_crud_api_contract() -> None:
    client = TestClient(app)
    workpackage_id = f"wp_crud_{uuid4().hex[:8]}"
    version = "v1.0.0"

    create_resp = client.post(
        "/v1/governance/observability/runtime/workpackages",
        json={
            "workpackage_id": workpackage_id,
            "version": version,
            "name": "地址治理样例",
            "objective": "地址标准化与验真",
            "status": "created",
        },
    )
    assert create_resp.status_code == 200
    create_payload = create_resp.json()
    assert create_payload.get("code") == "OK"
    data = create_payload.get("data") or {}
    assert data.get("workpackage_id") == workpackage_id
    assert data.get("version") == version

    list_resp = client.get(
        "/v1/governance/observability/runtime/workpackages",
        params={"q": workpackage_id, "limit": 20, "offset": 0},
    )
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload.get("code") == "OK"
    items = ((list_payload.get("data") or {}).get("items")) or []
    assert any((x.get("workpackage_id") == workpackage_id and x.get("version") == version) for x in items if isinstance(x, dict))

    detail_resp = client.get(f"/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}")
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.json()
    assert detail_payload.get("code") == "OK"
    assert ((detail_payload.get("data") or {}).get("workpackage_id")) == workpackage_id

    update_resp = client.put(
        f"/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}",
        json={"objective": "地址标准化+验真+图谱", "status": "packaged"},
    )
    assert update_resp.status_code == 200
    update_payload = update_resp.json()
    assert update_payload.get("code") == "OK"
    assert ((update_payload.get("data") or {}).get("status")) == "packaged"

    delete_resp = client.delete(f"/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}")
    assert delete_resp.status_code == 200
    delete_payload = delete_resp.json()
    assert delete_payload.get("code") == "OK"

    after_delete = client.get(f"/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}")
    assert after_delete.status_code == 404


def test_runtime_workpackage_crud_invalid_payload() -> None:
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/workpackages",
        json={"version": "v1.0.0", "objective": "missing id"},
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "INVALID_PAYLOAD"


def test_runtime_workpackage_crud_writes_trace_log(monkeypatch, tmp_path) -> None:
    trace_path = tmp_path / "runtime_api_trace.jsonl"
    monkeypatch.setenv("RUNTIME_API_TRACE_LOG", str(trace_path))

    client = TestClient(app)
    workpackage_id = f"wp_trace_{uuid4().hex[:8]}"
    version = "v1.0.0"

    resp = client.post(
        "/v1/governance/observability/runtime/workpackages",
        json={
            "workpackage_id": workpackage_id,
            "version": version,
            "name": "trace case",
            "objective": "trace log coverage",
            "status": "created",
        },
    )
    assert resp.status_code == 200
    list_resp = client.get("/v1/governance/observability/runtime/workpackages", params={"q": workpackage_id})
    assert list_resp.status_code == 200
    del_resp = client.delete(f"/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}")
    assert del_resp.status_code == 200

    assert trace_path.exists()
    rows = [json.loads(x) for x in trace_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    event_types = {str(row.get("event_type") or "") for row in rows}
    assert "runtime_workpackage_crud_create" in event_types
    assert "runtime_workpackage_crud_list" in event_types
    assert "runtime_workpackage_crud_delete" in event_types
