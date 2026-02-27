from services.governance_api.app.repositories.governance_repository import REPOSITORY


def test_log_blocked_confirmation_contains_required_fields() -> None:
    event = REPOSITORY.log_blocked_confirmation(
        event_type="llm_call_blocked",
        caller="factory_agent",
        payload={
            "reason": "llm_unavailable",
            "confirmation_user": "owner",
            "confirmation_decision": "switch_model",
            "confirmation_timestamp": "2026-02-27T10:00:00Z",
        },
    )
    assert event["event_type"] == "llm_call_blocked"
    payload = event.get("payload") or {}
    assert payload.get("reason") == "llm_unavailable"
    assert payload.get("confirmation_user") == "owner"
    assert payload.get("confirmation_decision") == "switch_model"
    assert payload.get("confirmation_timestamp")
