from __future__ import annotations

from pathlib import Path

import pytest

from playwright import sync_api
expect = sync_api.expect


def test_runtime_observability_upload_batch_from_csv(page, base_url):
    fixture_csv = (
        Path(__file__).resolve().parents[2]
        / "testdata"
        / "fixtures"
        / "runtime_upload"
        / "addresses_basic_10.csv"
    )
    assert fixture_csv.exists()

    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")
    expect(page.get_by_text("上传地址批次并执行任务")).to_be_visible()

    page.locator("#uploadFile").set_input_files(str(fixture_csv))
    page.wait_for_function(
        "() => (document.querySelector('#uploadText')?.value || '').trim().length > 0",
        timeout=10000,
    )
    page.get_by_role("button", name="上传并执行").click()

    status = page.locator("#uploadStatus")
    # Real runtime/LLM mode may take longer than test window; assert task creation visibility instead.
    expect(status).to_contain_text("执行", timeout=30000)

    page.get_by_role("button", name="刷新观测数据").click()
    expect(page.locator("#taskRows")).to_contain_text("task_", timeout=60000)
