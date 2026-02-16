import pytest

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


def test_observability_live_page_renders_core_sections(page, base_url):
    page.goto(f"{base_url}/v1/governance/lab/observability/view?env=dev", wait_until="domcontentloaded")

    expect(page.get_by_role("heading", name="系统可观测性管理看板")).to_be_visible()
    expect(page.get_by_text("一键进入 SQL 交互查询")).to_be_visible()

    expect(page.get_by_text("测试结果视图")).to_be_visible()
    expect(page.get_by_text("执行过程视图")).to_be_visible()
    expect(page.get_by_text("SQL交互查询")).to_be_visible()
    expect(page.get_by_role("heading", name="分层门槛状态（工作包/工作线/项目）")).to_be_visible()
    expect(page.get_by_role("heading", name="失败分类")).to_be_visible()


def test_observability_live_page_updates_connection_state(page, base_url):
    page.goto(f"{base_url}/v1/governance/lab/observability/view?env=staging", wait_until="domcontentloaded")
    last_ts = page.locator("#asOf")
    expect(last_ts).not_to_have_text("-", timeout=8000)
