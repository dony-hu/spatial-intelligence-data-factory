import pytest

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


def test_lab_replay_page_renders_core_sections(page, base_url, lab_change_context):
    change_id = lab_change_context["change_id"]
    page.goto(f"{base_url}/v1/governance/lab/change_requests/{change_id}/view", wait_until="domcontentloaded")

    expect(page.get_by_role("heading", name="Lab Change Request Replay")).to_be_visible()
    expect(page.get_by_text(f"change_id: {change_id}")).to_be_visible()

    expect(page.get_by_role("heading", name="Scorecard")).to_be_visible()
    expect(page.get_by_role("heading", name="Ruleset Diff")).to_be_visible()
    expect(page.get_by_role("heading", name="Improved Samples (Top 3)")).to_be_visible()
    expect(page.get_by_role("heading", name="Worsened Samples (Top 3)")).to_be_visible()
    expect(page.get_by_role("heading", name="Audit Events")).to_be_visible()

    # Pending by default: activation must be hard-gated.
    expect(page.get_by_text("activate_allowed: false")).to_be_visible()


def test_lab_replay_page_reflects_approval_and_activation_path(page, base_url, lab_change_context, governance_api):
    change_id = lab_change_context["change_id"]
    to_ruleset_id = lab_change_context["to_ruleset_id"]

    page.goto(f"{base_url}/v1/governance/lab/change_requests/{change_id}/view", wait_until="domcontentloaded")
    expect(page.get_by_text("activate_allowed: false")).to_be_visible()

    governance_api.post(
        f"/v1/governance/change-requests/{change_id}/approve",
        {"approver": "admin", "comment": "approve for web e2e"},
    )

    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_text("activate_allowed: true")).to_be_visible()

    activated = governance_api.post(
        f"/v1/governance/rulesets/{to_ruleset_id}/activate",
        {"change_id": change_id, "caller": "admin", "reason": "web e2e activation"},
    )
    assert activated["activated"] is True
