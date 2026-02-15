from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_worker.app.core.queue import run_in_memory_all


def test_review_decision() -> None:
    client = TestClient(app)
    submit = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-654321",
            "batch_name": "batch-b",
            "ruleset_id": "default",
            "records": [{"raw_id": "r2", "raw_text": "杭州市西湖区文三路90号"}],
        },
    )
    task_id = submit.json()["task_id"]
    processed = run_in_memory_all()
    assert processed >= 1

    before_result = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert before_result.status_code == 200
    assert len(before_result.json()["results"]) == 1

    ruleset = REPOSITORY.get_ruleset("default")
    before_total_reviews = (
        ruleset.get("config_json", {}).get("feedback_counters", {}).get("total_reviews", 0) if ruleset else 0
    )

    resp = client.post(
        f"/v1/governance/reviews/{task_id}/decision",
        json={"review_status": "edited", "final_canon_text": "杭州市西湖区文三路90号A座", "reviewer": "qa"},
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True
    assert resp.json()["updated_count"] == 1
    assert resp.json()["target_raw_id"] is None

    status_resp = client.get(f"/v1/governance/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "REVIEWED"

    after_result = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert after_result.status_code == 200
    items = after_result.json()["results"]
    assert len(items) == 1
    assert items[0]["canon_text"] == "杭州市西湖区文三路90号A座"
    assert items[0]["strategy"] == "human_edited"
    assert any(
        item.get("source") == "human_review" and item.get("review_status") == "edited"
        for item in items[0]["evidence"]["items"]
    )

    ruleset_after = REPOSITORY.get_ruleset("default")
    counters = ruleset_after.get("config_json", {}).get("feedback_counters", {}) if ruleset_after else {}
    assert counters.get("total_reviews", 0) == before_total_reviews + 1
    assert counters.get("review_edited", 0) >= 1


def test_review_decision_target_raw_id_only_updates_one_record() -> None:
    client = TestClient(app)
    submit = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-raw-target-001",
            "batch_name": "batch-targeted-review",
            "ruleset_id": "default",
            "records": [
                {"raw_id": "r-target-1", "raw_text": "深圳市南山区科技园科苑路1号"},
                {"raw_id": "r-target-2", "raw_text": "深圳市南山区科技园科苑路2号"},
            ],
        },
    )
    assert submit.status_code == 200
    task_id = submit.json()["task_id"]

    processed = run_in_memory_all()
    assert processed >= 1

    before = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert before.status_code == 200
    before_items = {item["raw_id"]: item for item in before.json()["results"]}
    assert set(before_items.keys()) == {"r-target-1", "r-target-2"}

    decision = client.post(
        f"/v1/governance/reviews/{task_id}/decision",
        json={
            "raw_id": "r-target-2",
            "review_status": "edited",
            "final_canon_text": "深圳市南山区科技园科苑路2号B栋",
            "reviewer": "qa-target",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["updated_count"] == 1
    assert decision.json()["target_raw_id"] == "r-target-2"

    after = client.get(f"/v1/governance/tasks/{task_id}/result")
    assert after.status_code == 200
    after_items = {item["raw_id"]: item for item in after.json()["results"]}

    assert after_items["r-target-2"]["canon_text"] == "深圳市南山区科技园科苑路2号B栋"
    assert after_items["r-target-2"]["strategy"] == "human_edited"
    assert any(
        item.get("source") == "human_review" and item.get("raw_id") == "r-target-2"
        for item in after_items["r-target-2"]["evidence"]["items"]
    )

    assert after_items["r-target-1"]["canon_text"] == before_items["r-target-1"]["canon_text"]
    assert after_items["r-target-1"]["strategy"] == before_items["r-target-1"]["strategy"]
    assert len(after_items["r-target-1"]["evidence"]["items"]) == len(before_items["r-target-1"]["evidence"]["items"])
