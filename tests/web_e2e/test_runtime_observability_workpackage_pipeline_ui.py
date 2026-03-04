from __future__ import annotations

import re

import pytest

from playwright import sync_api
expect = sync_api.expect


def test_runtime_observability_workpackage_panel_visible(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")
    expect(page.get_by_text("工作包链路观测")).to_be_visible()
    expect(page.locator("#workpackageRows")).to_be_visible()
    expect(page.get_by_test_id("wp-selector")).to_be_visible()
    page.get_by_role("button", name="灌入链路样例").click()
    expect(page.locator("#wpSeedStatus")).to_contain_text("已灌入链路样例", timeout=30000)
    expect(page.locator("#workpackageRows")).not_to_contain_text("暂无工作包链路数据", timeout=30000)
    first_row_link = page.locator("#workpackageRows .task-link").first
    expect(first_row_link).to_be_visible(timeout=30000)
    first_row_link.click()
    expect(page.get_by_test_id("wp-selector")).to_have_value(re.compile(r".+@.+"), timeout=30000)
    expect(page.get_by_test_id("workpackage-blueprint-meta")).to_contain_text("工作包：", timeout=30000)
