from fastapi.testclient import TestClient

from services.governance_api.app.main import app


def test_ruleset_update_and_publish_is_blocked_without_approval_gate() -> None:
    client = TestClient(app)
    update_resp = client.put(
        "/v1/governance/rulesets/rule-a",
        json={"version": "v1", "is_active": False, "config_json": {"thresholds": {"t_high": 0.8}}},
    )
    assert update_resp.status_code == 200

    publish_resp = client.post(
        "/v1/governance/rulesets/rule-a/publish",
        json={"operator": "ops", "reason": "promote v1"},
    )
    assert publish_resp.status_code == 409
    assert publish_resp.json()["detail"]["code"] == "APPROVAL_GATE_REQUIRED"


def test_change_request_and_activation_hard_gate() -> None:
    client = TestClient(app)

    create_ruleset_resp = client.put(
        "/v1/governance/rulesets/rule-b",
        json={
            "version": "v2",
            "is_active": False,
            "config_json": {"thresholds": {"t_high": 0.82, "t_low": 0.58}},
        },
    )
    assert create_ruleset_resp.status_code == 200

    create_change_resp = client.post(
        "/v1/governance/change-requests",
        json={
            "from_ruleset_id": "default",
            "to_ruleset_id": "rule-b",
            "baseline_task_id": "task-baseline-1",
            "candidate_task_id": "task-candidate-1",
            "diff": {"thresholds": {"t_high": 0.82, "t_low": 0.58}},
            "scorecard": {"delta": {"auto_pass_rate": 0.01}},
            "recommendation": "accept",
            "evidence_bullets": ["auto pass up", "human required stable", "consistency stable"],
        },
    )
    assert create_change_resp.status_code == 200
    change_id = create_change_resp.json()["change_id"]
    assert create_change_resp.json()["status"] == "pending"

    activate_before_approval = client.post(
        "/v1/governance/rulesets/rule-b/activate",
        json={"change_id": change_id, "caller": "admin", "reason": "promote"},
    )
    assert activate_before_approval.status_code == 409
    assert activate_before_approval.json()["detail"]["code"] == "APPROVAL_PENDING"

    reject_resp = client.post(
        f"/v1/governance/change-requests/{change_id}/reject",
        json={"reviewer": "qa-admin", "reason": "quality gate failed"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"

    activate_after_reject = client.post(
        "/v1/governance/rulesets/rule-b/activate",
        json={"change_id": change_id, "caller": "admin"},
    )
    assert activate_after_reject.status_code == 409
    assert activate_after_reject.json()["detail"]["code"] == "APPROVAL_REJECTED"

    approve_resp = client.post(
        f"/v1/governance/change-requests/{change_id}/approve",
        json={"approver": "qa-admin", "comment": "looks good"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    activate_non_admin = client.post(
        "/v1/governance/rulesets/rule-b/activate",
        json={"change_id": change_id, "caller": "operator"},
    )
    assert activate_non_admin.status_code == 403
    assert activate_non_admin.json()["detail"]["code"] == "CALLER_NOT_AUTHORIZED"

    activate_resp = client.post(
        "/v1/governance/rulesets/rule-b/activate",
        json={"change_id": change_id, "caller": "admin"},
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["activated"] is True
    assert activate_resp.json()["active_ruleset_id"] == "rule-b"


def test_activate_ruleset_rejects_unknown_change_request() -> None:
    client = TestClient(app)

    create_ruleset_resp = client.put(
        "/v1/governance/rulesets/rule-c",
        json={"version": "v3", "is_active": False, "config_json": {"thresholds": {"t_high": 0.83, "t_low": 0.57}}},
    )
    assert create_ruleset_resp.status_code == 200

    activate_missing_change = client.post(
        "/v1/governance/rulesets/rule-c/activate",
        json={"change_id": "chg_not_exists", "caller": "admin"},
    )
    assert activate_missing_change.status_code == 409
    assert activate_missing_change.json()["detail"]["code"] == "APPROVAL_MISSING"
