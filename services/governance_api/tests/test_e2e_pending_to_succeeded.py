import os

from fastapi.testclient import TestClient

from services.governance_api.app.main import app


class _RuntimeResultStub:
    def model_dump(self) -> dict:
        return {"strategy": "auto_accept", "confidence": 0.95, "evidence": {"items": []}}


class _RuntimeStub:
    def run_task(self, task_context: dict, ruleset: dict):
        return _RuntimeResultStub()


def test_e2e_pending_to_succeeded(monkeypatch) -> None:
    os.environ["GOVERNANCE_QUEUE_MODE"] = "sync"
    monkeypatch.setattr(
        "services.governance_worker.app.jobs.governance_job.get_runtime",
        lambda: _RuntimeStub(),
    )
    client = TestClient(app)
    payload = {
        "idempotency_key": "idem-e2e-001",
        "batch_name": "batch-e2e",
        "ruleset_id": "default",
        "records": [{"raw_id": "e2e-r1", "raw_text": "上海市浦东新区世纪大道100号"}],
    }

    submit_resp = client.post("/v1/governance/tasks", json=payload)
    assert submit_resp.status_code == 200
    task_id = submit_resp.json()["task_id"]
    assert submit_resp.json()["status"] == "SUCCEEDED"

    status_before = client.get(f"/v1/governance/tasks/{task_id}").json()["status"]
    assert status_before == "SUCCEEDED"

    status_after = client.get(f"/v1/governance/tasks/{task_id}").json()["status"]
    assert status_after == "SUCCEEDED"

    result_resp = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert result_resp.status_code == 200
    assert len(result_resp.json()["results"]) == 1
