from __future__ import annotations

import json
import os
from uuid import uuid4

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_api.app.services.governance_service import GOVERNANCE_SERVICE


def test_runtime_upload_batch_creates_task_and_visible_in_runtime_tasks(monkeypatch) -> None:
    client = TestClient(app)
    task_id = f"task_runtime_upload_{uuid4().hex[:8]}"

    def _fake_submit_task(batch_name: str, ruleset_id: str, records: list[dict]) -> dict:
        REPOSITORY.create_task(
            task_id=task_id,
            batch_name=batch_name,
            ruleset_id=ruleset_id,
            status="SUCCEEDED",
            queue_backend="sync",
            queue_message="executed",
            trace_id=f"trace_{task_id}",
        )
        REPOSITORY.save_results(
            task_id=task_id,
            results=[
                {
                    "raw_id": rec["raw_id"],
                    "canon_text": rec["raw_text"],
                    "confidence": 0.88,
                    "strategy": "auto_accept",
                    "evidence": {"items": [{"kind": "upload_batch_test"}]},
                }
                for rec in records
            ],
            raw_records=records,
        )
        REPOSITORY.set_task_status(task_id, "SUCCEEDED")
        return {"task_id": task_id, "trace_id": f"trace_{task_id}", "status": "SUCCEEDED"}

    monkeypatch.setattr(GOVERNANCE_SERVICE, "submit_task", _fake_submit_task)

    resp = client.post(
        "/v1/governance/observability/runtime/upload-batch",
        json={
            "batch_name": "upload-batch-test",
            "ruleset_id": "default",
            "addresses": [
                "上海市徐汇区肇嘉浜路111号",
                "北京市朝阳区建国路88号",
                "深圳市南山区科技园南区8栋",
            ],
            "actor": "tester",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["task_id"] == task_id
    assert int(payload.get("record_count") or 0) == 3

    tasks_resp = client.get("/v1/governance/observability/runtime/tasks?window=24h&limit=100&page=1")
    assert tasks_resp.status_code == 200
    items = tasks_resp.json().get("items", [])
    assert any(str(item.get("task_id") or "") == task_id for item in items)


def test_runtime_upload_batch_invalid_payload_when_workpackage_missing_version() -> None:
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/upload-batch",
        json={
            "batch_name": "upload-batch-invalid",
            "workpackage_id": "wp_only_id",
            "addresses": ["上海市徐汇区肇嘉浜路111号"],
        },
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "INVALID_PAYLOAD"


def test_runtime_upload_batch_invalid_payload_when_ruleset_conflicts_with_workpackage() -> None:
    client = TestClient(app)
    resp = client.post(
        "/v1/governance/observability/runtime/upload-batch",
        json={
            "batch_name": "upload-batch-conflict",
            "ruleset_id": "advanced_ruleset",
            "workpackage_id": "wp_conflict",
            "version": "v1.0.0",
            "addresses": ["上海市徐汇区肇嘉浜路111号"],
        },
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "INVALID_PAYLOAD"


def test_runtime_upload_batch_gate_blocks_packaged_without_confirm_generate() -> None:
    client = TestClient(app)
    workpackage_id = f"wp_gate_gen_{uuid4().hex[:8]}"
    version = "v1.0.0"
    resp = client.post(
        "/v1/governance/observability/runtime/upload-batch",
        json={
            "batch_name": "upload-batch-gate-generate",
            "workpackage_id": workpackage_id,
            "version": version,
            "addresses": ["上海市徐汇区肇嘉浜路111号"],
            "confirmations": ["confirm_dryrun_result", "confirm_publish"],
            "actor": "tester",
        },
    )
    assert resp.status_code == 409
    detail = resp.json().get("detail") or {}
    assert detail.get("code") == "WORKPACKAGE_GATE_BLOCKED"

    events_resp = client.get(
        "/v1/governance/observability/runtime/workpackage-events"
        f"?workpackage_id={workpackage_id}&version={version}&window=24h"
    )
    assert events_resp.status_code == 200
    items = (events_resp.json() or {}).get("items") or []
    event_types = {str(item.get("event_type") or "") for item in items}
    assert "workpackage_packaged" not in event_types


def test_runtime_upload_batch_gate_blocks_submitted_without_confirm_publish() -> None:
    client = TestClient(app)
    workpackage_id = f"wp_gate_pub_{uuid4().hex[:8]}"
    version = "v1.0.0"
    resp = client.post(
        "/v1/governance/observability/runtime/upload-batch",
        json={
            "batch_name": "upload-batch-gate-publish",
            "workpackage_id": workpackage_id,
            "version": version,
            "addresses": [
                "上海市徐汇区肇嘉浜路111号",
                "北京市朝阳区建国路88号",
            ],
            "confirmations": ["confirm_generate", "confirm_dryrun_result"],
            "actor": "tester",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert str(payload.get("status") or "").upper() == "BLOCKED"
    report = payload.get("dryrun_report") or {}
    assert isinstance(report.get("records"), list)
    graph = report.get("spatial_graph") or {}
    for key in ("nodes", "edges", "metrics", "failed_row_refs", "build_status"):
        assert key in graph

    events_resp = client.get(
        "/v1/governance/observability/runtime/workpackage-events"
        f"?workpackage_id={workpackage_id}&version={version}&window=24h"
    )
    assert events_resp.status_code == 200
    items = (events_resp.json() or {}).get("items") or []
    event_types = {str(item.get("event_type") or "") for item in items}
    assert "workpackage_packaged" in event_types
    assert "runtime_submit_requested" not in event_types


def test_runtime_upload_batch_by_workpackage_success_with_dryrun_report() -> None:
    client = TestClient(app)
    workpackage_id = f"wp_run_{uuid4().hex[:8]}"
    version = "v1.0.0"
    resp = client.post(
        "/v1/governance/observability/runtime/upload-batch",
        json={
            "batch_name": "upload-batch-workpackage",
            "workpackage_id": workpackage_id,
            "version": version,
            "addresses": [
                "上海市徐汇区肇嘉浜路111号",
                "北京市朝阳区建国路88号",
            ],
            "confirmations": ["confirm_generate", "confirm_dryrun_result", "confirm_publish"],
            "actor": "tester",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert str(payload.get("workpackage_id") or "") == workpackage_id
    assert str(payload.get("version") or "") == version
    assert str(payload.get("runtime_receipt_id") or "").strip() != ""

    report = payload.get("dryrun_report") or {}
    records = report.get("records") or []
    assert records
    row = records[0]
    for key in ("normalization", "entity_parsing", "address_validation"):
        assert key in row
    graph = report.get("spatial_graph") or {}
    for key in ("nodes", "edges", "metrics", "failed_row_refs", "build_status"):
        assert key in graph


def test_runtime_upload_batch_writes_trace_log(monkeypatch, tmp_path) -> None:
    trace_path = tmp_path / "runtime_api_trace.jsonl"
    monkeypatch.setenv("RUNTIME_API_TRACE_LOG", str(trace_path))
    client = TestClient(app)
    workpackage_id = f"wp_trace_upload_{uuid4().hex[:8]}"
    version = "v1.0.0"
    resp = client.post(
        "/v1/governance/observability/runtime/upload-batch",
        json={
            "batch_name": "upload-batch-trace",
            "workpackage_id": workpackage_id,
            "version": version,
            "addresses": ["上海市徐汇区肇嘉浜路111号"],
            "confirmations": ["confirm_generate", "confirm_dryrun_result", "confirm_publish"],
            "actor": "tester",
        },
    )
    assert resp.status_code == 200
    assert trace_path.exists()
    rows = [json.loads(x) for x in trace_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    upload_rows = [x for x in rows if str(x.get("event_type") or "") == "runtime_upload_batch"]
    assert upload_rows
    assert any(str((x.get("status") or "")) == "ok" for x in upload_rows)
