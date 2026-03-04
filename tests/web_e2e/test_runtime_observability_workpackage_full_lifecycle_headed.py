from __future__ import annotations

import re

import pytest
from playwright import sync_api

expect = sync_api.expect


def test_runtime_observability_workpackage_full_lifecycle_visual_headed(page, base_url, tmp_path):
    if str(__import__("os").getenv("RUN_REAL_LLM_WEB_E2E", "0")) != "1":
        pytest.skip("set RUN_REAL_LLM_WEB_E2E=1 to run real full lifecycle web e2e")

    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    wp_selector = page.get_by_test_id("wp-selector")
    blueprint_cfg = page.get_by_test_id("workpackage-blueprint-config")

    prompt = (
        "请创建一个地址治理工作包并直接生成："
        "1）先按工厂架构上下文对齐；"
        "2）对齐输入输出schema（输入addresses[]，输出records[]+spatial_graph）；"
        "3）绑定可信数据Hub已注册API并列出接口；"
        "4）若缺失API，给出外部API建议、脚本方案与key需求；"
        "5）最终输出可执行脚本与执行计划。"
    )
    chat_input.fill(prompt)
    send_btn.click()

    expect(send_btn).to_be_enabled(timeout=180000)
    if not re.match(r".+@.+", str(wp_selector.input_value() or "").strip()):
        chat_input.fill("请继续完成工作包生成，并返回 workpackage_id@version。")
        send_btn.click()
        expect(send_btn).to_be_enabled(timeout=180000)

    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=90000)
    expect(page.locator("#chatLog .chat-row.agent").last).not_to_contain_text('{"status"', timeout=10000)

    expect(blueprint_cfg).to_contain_text("workpackage", timeout=90000)
    expect(blueprint_cfg).to_contain_text("architecture_context", timeout=90000)
    expect(blueprint_cfg).to_contain_text("io_contract", timeout=90000)
    expect(blueprint_cfg).to_contain_text("api_plan", timeout=90000)
    expect(blueprint_cfg).to_contain_text("execution_plan", timeout=90000)
    expect(blueprint_cfg).to_contain_text("scripts", timeout=90000)

    page.locator("#actGenerate").click()
    page.locator("#actDryrun").click()
    page.locator("#actPublish").click()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_contain_text("confirm_publish", timeout=15000)

    csv_lines = [
        "raw_text",
        "上海市徐汇区肇嘉浜路111号",
        "北京市朝阳区建国路88号",
        "广州市天河区体育西路101号",
        "深圳市南山区科技园科苑路15号",
        "杭州市西湖区文三路90号",
        "南京市鼓楼区中山北路1号",
        "成都市高新区天府大道北段1700号",
        "武汉市洪山区珞喻路1037号",
        "西安市雁塔区长安中路123号",
        "苏州市工业园区星湖街218号",
    ]
    csv_path = tmp_path / "full_lifecycle_addresses_10.csv"
    csv_path.write_text("\n".join(csv_lines), encoding="utf-8")
    page.locator("#sourceFile").set_input_files(str(csv_path))

    csv_input = page.get_by_test_id("csv-upload-input")
    csv_value = page.evaluate("() => document.querySelector('[data-testid=\"csv-upload-input\"]')?.value || ''")
    if "上海市徐汇区肇嘉浜路111号" not in csv_value:
        csv_input.fill("\n".join(csv_lines[1:]))
    expect(csv_input).to_have_value(re.compile(r".*上海市徐汇区肇嘉浜路111号.*", re.S), timeout=10000)

    page.get_by_test_id("upload-exec-button").click()

    expect(page.get_by_test_id("runtime-receipt-id")).not_to_have_text("-", timeout=120000)
    expect(page.get_by_test_id("dryrun-records-table")).to_contain_text("normalization", timeout=120000)
    expect(page.get_by_test_id("dryrun-records-table")).to_contain_text("entity_parsing", timeout=120000)
    expect(page.get_by_test_id("dryrun-records-table")).to_contain_text("address_validation", timeout=120000)
    expect(page.get_by_test_id("dryrun-graph-card")).to_contain_text("nodes=", timeout=120000)
    expect(page.get_by_test_id("dryrun-graph-card")).to_contain_text("edges=", timeout=120000)
    expect(page.get_by_test_id("dryrun-graph-card")).to_contain_text("build_status=", timeout=120000)

    wp_ref = str(wp_selector.input_value() or "")
    wp_id, wp_ver = wp_ref.split("@", 1)
    events_resp = page.request.get(
        f"{base_url}/v1/governance/observability/runtime/workpackage-events"
        f"?workpackage_id={wp_id}&version={wp_ver}&window=24h&limit=20"
    )
    assert events_resp.ok
    events_payload = events_resp.json()
    items = events_payload.get("items") or []
    assert isinstance(items, list) and len(items) >= 1
    one = items[0]
    assert "source_zh" in one and str(one.get("source_zh") or "").strip()
    assert "event_type_zh" in one and str(one.get("event_type_zh") or "").strip()
    assert "status_zh" in one and str(one.get("status_zh") or "").strip()
    payload_summary = one.get("payload_summary") or {}
    assert "pipeline_stage_zh" in payload_summary and str(payload_summary.get("pipeline_stage_zh") or "").strip()

    download_link = page.get_by_test_id("runtime-output-download-link")
    expect(download_link).to_be_visible(timeout=120000)
    href = str(download_link.get_attribute("href") or "").strip()
    assert href.startswith("/output/")
    dl_resp = page.request.get(f"{base_url}{href}")
    assert dl_resp.ok
