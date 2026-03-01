from __future__ import annotations

import pytest

from playwright import sync_api
expect = sync_api.expect


def test_runtime_observability_workpackage_panel_visible(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")
    expect(page.get_by_text("新增治理包链路观测")).to_be_visible()
    expect(page.locator("#workpackageRows")).to_be_visible()
    expect(page.locator("#wpTotal")).to_be_visible()
    expect(page.locator("#wpE2E")).to_be_visible()
    expect(page.locator("#wpSubmitRate")).to_be_visible()
    page.get_by_role("button", name="灌入链路样例").click()
    expect(page.locator("#wpSeedStatus")).to_contain_text("已灌入链路样例", timeout=30000)
    expect(page.locator("#workpackageRows")).not_to_contain_text("暂无工作包链路数据", timeout=30000)
    first_row_link = page.locator("#workpackageRows .task-link").first
    expect(first_row_link).to_be_visible(timeout=30000)
    first_row_link.click()
    expect(page.locator("#wpModalMask.show")).to_be_visible(timeout=10000)
    expect(page.locator("#wpProcessLogs")).to_contain_text("runtime_submit", timeout=30000)
