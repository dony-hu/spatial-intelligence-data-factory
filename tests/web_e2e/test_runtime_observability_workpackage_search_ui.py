from __future__ import annotations

import re

from playwright import sync_api

expect = sync_api.expect


def test_runtime_observability_workpackage_search_ui(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    seed_resp = page.request.post(
        f"{base_url}/v1/governance/observability/runtime/workpackages/seed-crud-demo?total=12&prefix=wp_seed_crud_ui"
    )
    assert seed_resp.ok

    search_input = page.get_by_test_id("workpackage-search-input")
    status_filter = page.get_by_test_id("workpackage-status-filter")
    search_btn = page.get_by_test_id("workpackage-search-button")
    reset_btn = page.get_by_test_id("workpackage-search-reset")
    result_box = page.get_by_test_id("workpackage-search-results")

    search_input.fill("wp_seed_crud_ui")
    status_filter.select_option("created")
    search_btn.click()

    expect(result_box).to_contain_text("命中", timeout=30000)
    expect(page.get_by_test_id("wp-selector")).to_have_value(re.compile(r".+@.+"), timeout=30000)
    expect(page.get_by_test_id("workpackage-blueprint-meta")).to_contain_text("工作包：", timeout=30000)

    reset_btn.click()
    expect(result_box).not_to_have_text("检索失败", timeout=30000)
