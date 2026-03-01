import os

from fastapi.testclient import TestClient

from services.governance_api.app.main import app


class _RuntimeResultStub:
    def model_dump(self) -> dict:
        return {"strategy": "auto_accept", "confidence": 0.95, "evidence": {"items": []}}


class _RuntimeStub:
    def run_task(self, task_context: dict, ruleset: dict):
        return _RuntimeResultStub()


def test_submit_task_and_query_result(monkeypatch) -> None:
    os.environ["GOVERNANCE_QUEUE_MODE"] = "sync"
    monkeypatch.setattr(
        "services.governance_worker.app.jobs.governance_job.get_runtime",
        lambda: _RuntimeStub(),
    )
    client = TestClient(app)
    payload = {
        "idempotency_key": "idem-123456",
        "batch_name": "batch-a",
        "ruleset_id": "default",
        "records": [{"raw_id": "r1", "raw_text": "深圳市南山区前海大道1号"}],
    }
    submit_resp = client.post("/v1/governance/tasks", json=payload)
    assert submit_resp.status_code == 200
    task_id = submit_resp.json()["task_id"]
    assert submit_resp.json()["status"] == "SUCCEEDED"

    status_resp = client.get(f"/v1/governance/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "SUCCEEDED"

    result_resp = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert result_resp.status_code == 200
    assert len(result_resp.json()["results"]) == 1

    final_status_resp = client.get(f"/v1/governance/tasks/{task_id}")
    assert final_status_resp.status_code == 200
    assert final_status_resp.json()["status"] == "SUCCEEDED"

    final_result_resp = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert final_result_resp.status_code == 200
    assert len(final_result_resp.json()["results"]) == 1


def test_submit_task_enqueue_failure_marks_blocked(monkeypatch) -> None:
    monkeypatch.delenv("GOVERNANCE_QUEUE_MODE", raising=False)
    monkeypatch.setattr(
        "services.governance_worker.app.jobs.governance_job.get_runtime",
        lambda: _RuntimeStub(),
    )
    client = TestClient(app)
    payload = {
        "idempotency_key": "idem-blocked-001",
        "batch_name": "batch-blocked",
        "ruleset_id": "default",
        "records": [{"raw_id": "r-blocked", "raw_text": "深圳市南山区科技园"}],
    }
    submit_resp = client.post("/v1/governance/tasks", json=payload)
    assert submit_resp.status_code == 200
    task_id = submit_resp.json()["task_id"]
    assert submit_resp.json()["status"] == "BLOCKED"

    status_resp = client.get(f"/v1/governance/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "BLOCKED"
