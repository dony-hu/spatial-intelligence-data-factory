from __future__ import annotations

from playwright import sync_api

expect = sync_api.expect


def test_runtime_observability_s2_15_testids_and_workpackage_upload(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    for testid in (
        "wp-selector",
        "csv-upload-input",
        "upload-exec-button",
        "confirm-timeline-panel",
        "dryrun-report-open",
        "dryrun-records-table",
        "dryrun-graph-card",
        "events-table",
        "event-view-mode-toggle",
        "runtime-receipt-id",
    ):
        expect(page.get_by_test_id(testid)).to_be_visible()

    page.get_by_role("button", name="灌入链路样例").click()
    expect(page.locator("#wpSeedStatus")).to_contain_text("已灌入链路样例", timeout=30000)
    first_wp = page.locator("#workpackageRows .task-link").first
    expect(first_wp).to_be_visible(timeout=30000)
    wp_id = (first_wp.get_attribute("data-workpackage-id") or "").strip()
    wp_ver = (first_wp.get_attribute("data-version") or "").strip()
    assert wp_id
    assert wp_ver

    page.get_by_test_id("wp-selector").fill(f"{wp_id}@{wp_ver}")
    page.get_by_test_id("csv-upload-input").fill("上海市徐汇区肇嘉浜路111号\n北京市朝阳区建国路88号")
    page.get_by_test_id("upload-exec-button").click()

    expect(page.locator("#uploadStatus")).to_contain_text("执行", timeout=30000)
    expect(page.get_by_test_id("runtime-receipt-id")).to_be_visible()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_be_visible()
    expect(page.get_by_test_id("dryrun-report-open")).to_be_visible()
