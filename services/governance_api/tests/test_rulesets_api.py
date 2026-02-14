from fastapi.testclient import TestClient

from services.governance_api.app.main import app


def test_ruleset_update_and_publish() -> None:
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
    assert publish_resp.status_code == 200
    assert publish_resp.json()["is_active"] is True
