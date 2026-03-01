import pytest

from playwright import sync_api
expect = sync_api.expect


def test_observability_live_page_renders_core_sections(page, base_url):
    page.goto(f"{base_url}/v1/governance/lab/observability/view?env=dev", wait_until="domcontentloaded")

    expect(page.get_by_role("heading", name="可观测性总览")).to_be_visible()
    expect(page.get_by_role("heading", name="决策动作清单")).to_be_visible()
    expect(page.get_by_role("heading", name="趋势摘要（24h）")).to_be_visible()


def test_observability_live_page_updates_connection_state(page, base_url):
    page.goto(f"{base_url}/v1/governance/lab/observability/view?env=staging", wait_until="domcontentloaded")
    last_ts = page.locator("#asOf")
    expect(last_ts).not_to_have_text("-", timeout=8000)
