from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")
os.environ["OBSERVABILITY_ADMIN_TOKEN"] = os.getenv("OBSERVABILITY_ADMIN_TOKEN", "admin-token-local")
os.environ["OBSERVABILITY_ONCALL_TOKEN"] = os.getenv("OBSERVABILITY_ONCALL_TOKEN", "oncall-token-local")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_sensitive_task(task_id: str) -> None:
    REPOSITORY.create_task(
        task_id=task_id,
        batch_name="runtime-compliance-seed",
        ruleset_id="default",
        status="SUCCEEDED",
        queue_backend="sync",
        queue_message="seeded",
        trace_id=f"trace_{task_id}",
    )
    REPOSITORY.save_results(
        task_id=task_id,
        results=[
            {
                "raw_id": f"raw_{task_id}_01",
                "canon_text": "上海市徐汇区肇嘉浜路111号A栋",
                "confidence": 0.86,
                "strategy": "auto_accept",
                "evidence": {"items": [{"source": "external_api", "name": "张三", "phone": "13800138000"}]},
            }
        ],
        raw_records=[{"raw_id": f"raw_{task_id}_01", "raw_text": "上海市徐汇区肇嘉浜路111号A栋"}],
    )


def test_viewer_can_read_detail_but_data_is_masked_and_audited() -> None:
    client = TestClient(app)
    task_id = "task_runtime_compliance_mask_001"
    _seed_sensitive_task(task_id)

    resp = client.get(f"/v1/governance/observability/runtime/tasks/{task_id}/detail?role=viewer&actor=test_viewer")
    assert resp.status_code == 200
    payload = resp.json()
    source_data = payload.get("source_data") or []
    assert source_data
    assert "*" in str(source_data[0].get("raw_text") or "")
    governance_results = payload.get("governance_results") or []
    assert governance_results
    assert "*" in str(governance_results[0].get("canon_text") or "")

    audit_found = False
    for evt in REPOSITORY.list_audit_events():
        p = evt.get("payload") if isinstance(evt.get("payload"), dict) else {}
        if str(evt.get("event_type") or "") == "runtime_detail_access" and str(p.get("task_id") or "") == task_id:
            audit_found = True
            break
    assert audit_found


def test_ack_requires_oncall_or_admin() -> None:
    client = TestClient(app)
    created = REPOSITORY.create_observation_alert(
        alert_rule="compliance_ack_test",
        severity="P2",
        trigger_value=1.0,
        threshold_value=0.0,
    )
    alert_id = str(created.get("alert_id") or "")
    assert alert_id

    viewer_ack = client.post(f"/v1/governance/observability/alerts/{alert_id}/ack?role=viewer&actor=v", json={"actor": "v"})
    assert viewer_ack.status_code == 403
    assert viewer_ack.json().get("detail", {}).get("code") == "ROLE_FORBIDDEN"

    oncall_ack = client.post(
        f"/v1/governance/observability/alerts/{alert_id}/ack?role=oncall&actor=ops",
        headers={"x-observability-token": "oncall-token-local"},
        json={"actor": "ops"},
    )
    assert oncall_ack.status_code == 200
    assert oncall_ack.json().get("status") == "acked"


def test_export_requires_admin_and_audit_query_requires_admin() -> None:
    client = TestClient(app)
    task_id = "task_runtime_compliance_export_001"
    _seed_sensitive_task(task_id)

    no_admin = client.get(f"/v1/governance/observability/runtime/tasks/{task_id}/export?role=oncall&actor=ops")
    assert no_admin.status_code == 403
    assert no_admin.json().get("detail", {}).get("code") == "ROLE_FORBIDDEN"

    admin_export = client.get(
        f"/v1/governance/observability/runtime/tasks/{task_id}/export?role=admin&actor=admin_user",
        headers={"x-observability-token": "admin-token-local"},
    )
    assert admin_export.status_code == 200
    export_payload = admin_export.json()
    assert export_payload.get("task", {}).get("task_id") == task_id

    forbidden_audit = client.get("/v1/governance/observability/runtime/compliance/audit?role=viewer")
    assert forbidden_audit.status_code == 403

    audit_ok = client.get(
        "/v1/governance/observability/runtime/compliance/audit?role=admin&limit=200",
        headers={"x-observability-token": "admin-token-local"},
    )
    assert audit_ok.status_code == 200
    audit_payload = audit_ok.json()
    assert "items" in audit_payload
    assert any(str(item.get("event_type") or "") == "runtime_task_export" for item in audit_payload.get("items", []))
