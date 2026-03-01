from __future__ import annotations

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
