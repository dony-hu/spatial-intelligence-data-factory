from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_worker.app.core.queue import run_in_memory_all


def test_submit_task_and_query_result() -> None:
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
    assert submit_resp.json()["status"] == "PENDING"

    status_resp = client.get(f"/v1/governance/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "PENDING"

    result_resp = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert result_resp.status_code == 200
    assert len(result_resp.json()["results"]) == 0

    processed = run_in_memory_all()
    assert processed >= 1

    final_status_resp = client.get(f"/v1/governance/tasks/{task_id}")
    assert final_status_resp.status_code == 200
    assert final_status_resp.json()["status"] == "SUCCEEDED"

    final_result_resp = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert final_result_resp.status_code == 200
    assert len(final_result_resp.json()["results"]) == 1
