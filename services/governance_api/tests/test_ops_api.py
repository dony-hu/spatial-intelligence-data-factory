from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_worker.app.core.queue import run_in_memory_all


def test_ops_summary_includes_task_review_metrics() -> None:
    client = TestClient(app)

    before = client.get("/v1/governance/ops/summary")
    assert before.status_code == 200
    before_json = before.json()

    submit = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-ops-001",
            "batch_name": "batch-ops",
            "ruleset_id": "default",
            "records": [{"raw_id": "ops-r1", "raw_text": "深圳市福田区福中三路100号"}],
        },
    )
    assert submit.status_code == 200
    task_id = submit.json()["task_id"]

    processed = run_in_memory_all()
    assert processed >= 1

    reviewed = client.post(
        f"/v1/governance/reviews/{task_id}/decision",
        json={"raw_id": "ops-r1", "review_status": "approved", "reviewer": "ops-qa"},
    )
    assert reviewed.status_code == 200

    after = client.get("/v1/governance/ops/summary")
    assert after.status_code == 200
    after_json = after.json()

    assert after_json["total_tasks"] >= before_json["total_tasks"] + 1
    assert after_json["total_results"] >= before_json["total_results"] + 1
    assert 0 <= after_json["avg_confidence"] <= 1
    assert after_json["active_ruleset_id"]
    assert "t_low" in after_json["thresholds"] and "t_high" in after_json["thresholds"]
    assert after_json["reviewed_tasks"] >= before_json.get("reviewed_tasks", 0) + 1
    assert isinstance(after_json["quality_gate_reasons"], list)


def test_ops_summary_supports_filters_and_threshold_override() -> None:
    client = TestClient(app)

    submit_a = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-ops-filter-a",
            "batch_name": "batch-filter-a",
            "ruleset_id": "default",
            "records": [{"raw_id": "ops-fa-1", "raw_text": "深圳市南山区粤海街道A"}],
        },
    )
    submit_b = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-ops-filter-b",
            "batch_name": "batch-filter-b",
            "ruleset_id": "default",
            "records": [{"raw_id": "ops-fb-1", "raw_text": "深圳市南山区粤海街道B"}],
        },
    )
    assert submit_a.status_code == 200
    assert submit_b.status_code == 200

    processed = run_in_memory_all()
    assert processed >= 2

    task_a = submit_a.json()["task_id"]
    filtered = client.get(f"/v1/governance/ops/summary?task_id={task_a}&t_low=0.99")
    assert filtered.status_code == 200
    filtered_json = filtered.json()

    assert filtered_json["total_tasks"] == 1
    assert filtered_json["total_results"] == 1
    assert filtered_json["thresholds"]["t_low"] == 0.99
    assert filtered_json["low_confidence_results"] >= 0
    assert "pending_review_exists" in filtered_json["quality_gate_reasons"]


def test_ops_summary_supports_ruleset_filter() -> None:
    client = TestClient(app)

    ruleset_resp = client.put(
        "/v1/governance/rulesets/rule-filter-1",
        json={"version": "v1", "is_active": False, "config_json": {"thresholds": {"t_high": 0.8, "t_low": 0.6}}},
    )
    assert ruleset_resp.status_code == 200

    submit_default = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-ops-ruleset-default",
            "batch_name": "batch-ruleset-default",
            "ruleset_id": "default",
            "records": [{"raw_id": "ops-rs-d1", "raw_text": "上海市徐汇区漕溪北路1号"}],
        },
    )
    submit_rule = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-ops-ruleset-custom",
            "batch_name": "batch-ruleset-custom",
            "ruleset_id": "rule-filter-1",
            "records": [{"raw_id": "ops-rs-c1", "raw_text": "上海市徐汇区漕溪北路2号"}],
        },
    )
    assert submit_default.status_code == 200
    assert submit_rule.status_code == 200

    processed = run_in_memory_all()
    assert processed >= 2

    filtered = client.get("/v1/governance/ops/summary?ruleset_id=rule-filter-1")
    assert filtered.status_code == 200
    filtered_json = filtered.json()

    assert filtered_json["total_tasks"] == 1
    assert filtered_json["total_results"] == 1


def test_ops_summary_supports_status_filter() -> None:
    client = TestClient(app)

    submit = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-ops-status-001",
            "batch_name": "batch-status",
            "ruleset_id": "default",
            "records": [{"raw_id": "ops-status-1", "raw_text": "广州市天河区体育东路1号"}],
        },
    )
    assert submit.status_code == 200
    task_id = submit.json()["task_id"]

    before = client.get("/v1/governance/ops/summary?status=REVIEWED")
    assert before.status_code == 200
    before_count = before.json()["total_tasks"]

    processed = run_in_memory_all()
    assert processed >= 1

    reviewed = client.post(
        f"/v1/governance/reviews/{task_id}/decision",
        json={"raw_id": "ops-status-1", "review_status": "approved", "reviewer": "ops-status"},
    )
    assert reviewed.status_code == 200

    reviewed_only = client.get("/v1/governance/ops/summary?status=REVIEWED")
    assert reviewed_only.status_code == 200
    reviewed_json = reviewed_only.json()
    assert reviewed_json["total_tasks"] >= before_count + 1
    assert reviewed_json["status_counts"].get("REVIEWED", 0) >= 1

    succeeded_only = client.get("/v1/governance/ops/summary?status=SUCCEEDED")
    assert succeeded_only.status_code == 200
    succeeded_json = succeeded_only.json()
    assert succeeded_json["status_counts"].get("REVIEWED", 0) == 0


def test_ops_summary_supports_recent_hours_filter() -> None:
    client = TestClient(app)

    before = client.get("/v1/governance/ops/summary?recent_hours=0")
    assert before.status_code == 200
    before_total = before.json()["total_tasks"]

    submit = client.post(
        "/v1/governance/tasks",
        json={
            "idempotency_key": "idem-ops-recent-hours-001",
            "batch_name": "batch-recent-hours",
            "ruleset_id": "default",
            "records": [{"raw_id": "ops-recent-1", "raw_text": "北京市海淀区中关村大街1号"}],
        },
    )
    assert submit.status_code == 200

    after = client.get("/v1/governance/ops/summary?recent_hours=1")
    assert after.status_code == 200
    after_json = after.json()
    assert after_json["total_tasks"] >= before_total + 1
