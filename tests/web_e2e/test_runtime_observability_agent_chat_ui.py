from __future__ import annotations

import json
import os
import re
from pathlib import Path

from playwright import sync_api
import pytest

expect = sync_api.expect
LONG_MULTI_TURN_TIMEOUT_MS = int(os.getenv("WEB_E2E_LONG_TURN_TIMEOUT_MS", "120000"))


def test_runtime_observability_manual_agent_chat_panel(page, base_url):
    page.goto(
        f"{base_url}/v1/governance/observability/runtime/view?window=24h",
        wait_until="domcontentloaded",
        timeout=90000,
    )
    expect(page.get_by_test_id("agent-chat-panel")).to_be_visible()
    expect(page.get_by_test_id("nanobot-memory-panel")).to_be_visible()
    expect(page.get_by_test_id("agent-chat-input")).to_be_visible()
    expect(page.get_by_test_id("agent-chat-send")).to_be_visible()
    expect(page.get_by_test_id("agent-chat-log")).to_be_visible()
    expect(page.locator("#llmAccordion")).to_be_visible()
    expect(page.locator("#wpMaintLogs")).to_be_visible()
    expect(page.get_by_test_id("memory-timeline-panel")).to_be_visible()
    expect(page.get_by_test_id("memory-summary-panel")).to_be_visible()
    expect(page.locator("#actGenerate")).to_be_visible()
    expect(page.locator("#actDryrun")).to_be_visible()
    expect(page.locator("#actPublish")).to_be_visible()

    page.get_by_test_id("agent-chat-input").fill("列出工作包")
    page.get_by_test_id("agent-chat-send").click()
    expect(page.get_by_test_id("agent-chat-log")).to_contain_text("列出工作包", timeout=30000)
    expect(page.locator("#llmAccordion")).to_contain_text("第 1 轮", timeout=30000)
    expect(page.get_by_test_id("memory-summary-panel")).not_to_contain_text("暂无记忆摘要", timeout=30000)
    expect(page.get_by_test_id("memory-boot-context")).to_contain_text("nanobot", timeout=30000)
    expect(page.get_by_test_id("memory-discovery-facts")).to_contain_text("列出工作包", timeout=30000)

    page.locator("#actGenerate").click()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_contain_text("confirm_generate", timeout=10000)


def test_runtime_observability_assistant_markdown_formatter(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")
    html = page.evaluate(
        """
        () => {
          if (typeof window.__formatAssistantText !== "function") {
            return "";
          }
          return window.__formatAssistantText("### 标题\\n---\\n1. 步骤一\\n2. 步骤二\\n**重点**");
        }
        """
    )
    assert "<h3" in html
    assert "<ol" in html
    assert "<strong>" in html


def test_runtime_observability_to_natural_chat_reply_handles_json_string(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")
    text = page.evaluate(
        """
        () => {
          if (typeof window.toNaturalChatReply !== "function") {
            return "";
          }
          return window.toNaturalChatReply(
            { message: '{"status":"ok","message":"这个话题我不太擅长。","suggestion":"你可以告诉我数据治理目标。"}' },
            ""
          );
        }
        """
    )
    assert "不太擅长" in text
    assert '{"status"' not in text


def test_runtime_observability_flexible_multi_turn_chat_flow(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    agent_rows = page.locator("#chatLog .chat-row.agent")
    user_rows = page.locator("#chatLog .chat-row.user")

    initial_agent_count = agent_rows.count()

    chat_input.fill("今天天气怎么样")
    send_btn.click()
    expect(agent_rows.last).to_contain_text("不太擅长", timeout=30000)
    expect(user_rows).to_have_count(1, timeout=30000)
    expect(agent_rows).to_have_count(initial_agent_count + 1, timeout=30000)

    chat_input.fill("数据量只有不超过100条；其他的你输出建议。")
    send_btn.click()
    expect(user_rows).to_have_count(2, timeout=30000)
    expect(agent_rows).to_have_count(initial_agent_count + 2, timeout=30000)
    expect(agent_rows.last).not_to_contain_text('"action"', timeout=30000)
    expect(agent_rows.last).not_to_contain_text('{"status"', timeout=30000)

    chat_input.fill("列出工作包")
    send_btn.click()
    expect(user_rows).to_have_count(3, timeout=30000)
    expect(agent_rows).to_have_count(initial_agent_count + 3, timeout=30000)
    expect(agent_rows.last).to_contain_text("已发布", timeout=30000)
    expect(page.locator("#llmAccordion")).to_contain_text("第 1 轮", timeout=30000)


def test_runtime_observability_web_e2e_long_multi_turn_workpackage_creation(page, base_url, tmp_path):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    agent_rows = page.locator("#chatLog .chat-row.agent")
    user_rows = page.locator("#chatLog .chat-row.user")
    wp_selector = page.get_by_test_id("wp-selector")

    dialogue_rounds = [
        "我们要做地址治理，请你按工厂流程引导我完成工作包创建。",
        "治理目标：地址标准化、地址验真、实体拆分、空间图谱输出。",
        "约束：首批不超过100条，优先低成本，可审计、可下载。",
        "干扰问题：今天天气如何？",
        "回到任务：请继续数据治理方案，不要偏题。",
        "请先列出你将使用的已注册可信数据Hub接口，并说明用途。",
        "如果已注册接口不足，请给最小外部依赖建议和key需求；若够用就直接推进。",
        "请按工作包协议收敛输入输出（输入addresses[]，输出records[]+spatial_graph）。",
        "我确认采用你建议的默认方案，请继续。",
        "现在请生成可执行工作包，并返回 workpackage_id@version。",
        "请复述执行计划：generate -> dryrun -> publish。",
        "最后列出当前工作包。",
    ]

    initial_agent_count = agent_rows.count()
    initial_user_count = user_rows.count()

    total_turns = 0
    for turn in dialogue_rounds:
        total_turns += 1
        chat_input.fill(turn)
        send_btn.click()
        expect(user_rows).to_have_count(initial_user_count + total_turns, timeout=LONG_MULTI_TURN_TIMEOUT_MS)
        expect(agent_rows).to_have_count(initial_agent_count + total_turns, timeout=LONG_MULTI_TURN_TIMEOUT_MS)

    # Real external LLM may occasionally timeout on a single turn; send recovery turns until wp is available.
    recovery_prompts = [
        "继续按照已对齐需求，直接生成工作包并返回 workpackage_id@version。",
        "请基于当前上下文再次生成工作包，确保包含地址标准化、验真、实体拆分、空间图谱。",
        "请最终确认并列出当前工作包。",
    ]
    for prompt in recovery_prompts:
        current_ref = str(wp_selector.input_value() or "").strip()
        if re.match(r".+@.+", current_ref):
            break
        total_turns += 1
        chat_input.fill(prompt)
        send_btn.click()
        expect(user_rows).to_have_count(initial_user_count + total_turns, timeout=LONG_MULTI_TURN_TIMEOUT_MS)
        expect(agent_rows).to_have_count(initial_agent_count + total_turns, timeout=LONG_MULTI_TURN_TIMEOUT_MS)

    latest_agent = agent_rows.last
    expect(latest_agent).not_to_contain_text('{"status"', timeout=10000)
    expect(latest_agent).not_to_contain_text('"action"', timeout=10000)

    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=45000)
    expect(page.locator("#llmAccordion")).to_contain_text("第", timeout=45000)
    expect(page.locator("#wpMaintLogs")).not_to_contain_text("暂无维护记录", timeout=45000)

    page.locator("#actGenerate").click()
    page.locator("#actDryrun").click()
    page.locator("#actPublish").click()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_contain_text("confirm_publish", timeout=10000)

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
    csv_path = tmp_path / "runtime_addresses_10.csv"
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
    expect(page.get_by_test_id("dryrun-graph-card")).to_contain_text("nodes=", timeout=120000)

    download_link = page.get_by_test_id("runtime-output-download-link")
    expect(download_link).to_be_visible(timeout=120000)
    href = (download_link.get_attribute("href") or "").strip()
    assert href.startswith("/output/")
    dl_resp = page.request.get(f"{base_url}{href}")
    assert dl_resp.ok


def test_runtime_observability_web_e2e_quick_workpackage_publish_and_dryrun_sfmap(page, base_url, tmp_path):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    agent_rows = page.locator("#chatLog .chat-row.agent")
    user_rows = page.locator("#chatLog .chat-row.user")
    wp_selector = page.get_by_test_id("wp-selector")

    initial_agent_count = agent_rows.count()
    initial_user_count = user_rows.count()

    minimal_dialogue = [
        "创建一个数据治理工作包：地址标准化、地址验真、空间实体拆分、空间图谱输出。",
        "数据源使用顺丰地图 API；目标是先跑通预验证再发布。",
        "按这个目标直接生成工作包，并准备执行。",
    ]
    for i, message in enumerate(minimal_dialogue, start=1):
        chat_input.fill(message)
        send_btn.click()
        expect(user_rows).to_have_count(initial_user_count + i, timeout=45000)
        expect(agent_rows).to_have_count(initial_agent_count + i, timeout=45000)

    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=45000)
    expect(page.locator("#llmAccordion")).to_contain_text("第 1 轮", timeout=45000)

    page.locator("#actGenerate").click()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_contain_text("confirm_generate", timeout=10000)
    page.locator("#actDryrun").click()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_contain_text("confirm_dryrun_result", timeout=10000)
    page.locator("#actPublish").click()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_contain_text("confirm_publish", timeout=10000)

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
    csv_path = tmp_path / "runtime_addresses_quick_10.csv"
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

    download_link = page.get_by_test_id("runtime-output-download-link")
    expect(download_link).to_be_visible(timeout=120000)
    href = (download_link.get_attribute("href") or "").strip()
    assert href.startswith("/output/")
    dl_resp = page.request.get(f"{base_url}{href}")
    assert dl_resp.ok


def test_runtime_observability_workpackage_blueprint_panel(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    wp_selector = page.get_by_test_id("wp-selector")

    chat_input.fill("创建一个数据治理工作包：地址标准化、地址验真、空间实体拆分、空间图谱输出。")
    send_btn.click()
    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=45000)

    expect(page.get_by_test_id("workpackage-blueprint-panel")).to_be_visible(timeout=15000)
    expect(page.get_by_test_id("workpackage-blueprint-meta")).to_contain_text("工作包：", timeout=45000)
    expect(page.get_by_test_id("workpackage-blueprint-apis")).to_contain_text("地址标准化", timeout=45000)
    expect(page.get_by_test_id("workpackage-blueprint-config")).to_contain_text("sources", timeout=45000)


def test_runtime_observability_contextual_workpackage_generation_contract(page, base_url):
    if os.getenv("RUN_REAL_LLM_WEB_E2E", "0") != "1":
        pytest.skip("set RUN_REAL_LLM_WEB_E2E=1 to run real long LLM web e2e")
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    wp_selector = page.get_by_test_id("wp-selector")
    initial_wp = wp_selector.input_value() or ""

    prompt = (
        "请基于数据治理工厂完整上下文创建工作包 ctx-e2e-v1.0.0："
        "1) 先说明与工作包相关的架构上下文；"
        "2) 对齐输入输出并给出精确schema；"
        "3) 明确使用可信数据Hub已注册API并列出接口；"
        "4) 若已注册API不足，建议外部API/数据源，给出拉取脚本和key需求，并注册到Hub扩展能力；"
        "5) 依赖对齐后输出可执行工具脚本与执行计划。"
    )
    expect(send_btn).to_be_enabled(timeout=120000)
    chat_input.fill(prompt)
    send_btn.click()
    expect(page.locator("#chatLog .chat-row.user")).to_have_count(1, timeout=45000)
    expect(send_btn).to_be_enabled(timeout=180000)
    expect(page.locator("#chatLog .chat-row.agent").last).to_contain_text("已生成", timeout=180000)
    if initial_wp.strip():
        page.wait_for_function(
            """
            (initial) => {
              const el = document.querySelector('[data-testid="wp-selector"]');
              return !!el && String(el.value || "").trim() !== String(initial || "").trim();
            }
            """,
            initial_wp,
            timeout=60000,
        )
    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=60000)
    expect(page.get_by_test_id("workpackage-blueprint-panel")).to_be_visible(timeout=15000)
    expect(page.get_by_test_id("workpackage-blueprint-meta")).to_contain_text("工作包：", timeout=45000)
    expect(page.get_by_test_id("workpackage-blueprint-config")).to_contain_text("architecture_context", timeout=45000)
    expect(page.get_by_test_id("workpackage-blueprint-config")).to_contain_text("input_schema", timeout=45000)
    expect(page.get_by_test_id("workpackage-blueprint-config")).to_contain_text("output_schema", timeout=45000)
    expect(page.get_by_test_id("workpackage-blueprint-config")).to_contain_text("api_plan", timeout=45000)
    expect(page.get_by_test_id("workpackage-blueprint-config")).to_contain_text("scripts", timeout=45000)
    expect(page.locator("#llmAccordion")).to_contain_text("architecture_context", timeout=45000)
    expect(page.locator("#llmAccordion")).to_contain_text("registered_api_catalog", timeout=45000)


def test_runtime_observability_web_e2e_generate_address_governance_workpackage_by_schema(page, base_url):
    if os.getenv("RUN_REAL_LLM_WEB_E2E", "0") != "1":
        pytest.skip("set RUN_REAL_LLM_WEB_E2E=1 to run real long LLM web e2e")

    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    wp_selector = page.get_by_test_id("wp-selector")
    wp_config_pre = page.get_by_test_id("workpackage-blueprint-config")

    prompt = (
        "请基于 workpackage_schema.v1 生成地址治理工作包 addr-case-schema-v1.0.0。"
        "输入是一批地址字段 addresses[]；输出必须包含 records[] 和 spatial_graph。"
        "records[] 每条必须含 normalization/entity_parsing/address_validation；"
        "spatial_graph 必须含 nodes/edges/metrics/failed_row_refs/build_status；"
        "并补齐 execution_plan.gates 与 scripts。"
    )

    expect(send_btn).to_be_enabled(timeout=60000)
    chat_input.fill(prompt)
    send_btn.click()

    expect(page.locator("#chatLog .chat-row.user").last).to_contain_text("workpackage_schema.v1", timeout=30000)
    expect(page.locator("#chatLog .chat-row.agent").last).to_contain_text("已生成", timeout=180000)
    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=60000)
    expect(page.get_by_test_id("workpackage-blueprint-panel")).to_be_visible(timeout=15000)
    expect(wp_config_pre).to_contain_text("io_contract", timeout=45000)
    expect(wp_config_pre).to_contain_text("execution_plan", timeout=45000)
    expect(wp_config_pre).to_contain_text("scripts", timeout=45000)

    raw = page.evaluate("() => document.querySelector('[data-testid=\"workpackage-blueprint-config\"]')?.textContent || '{}'")
    config = json.loads(raw)

    assert isinstance(config, dict)
    io_contract = config.get("io_contract") if isinstance(config.get("io_contract"), dict) else {}
    input_schema = io_contract.get("input_schema") if isinstance(io_contract.get("input_schema"), dict) else {}
    output_schema = io_contract.get("output_schema") if isinstance(io_contract.get("output_schema"), dict) else {}
    output_props = output_schema.get("properties") if isinstance(output_schema.get("properties"), dict) else {}
    records_schema = output_props.get("records") if isinstance(output_props.get("records"), dict) else {}
    records_item = records_schema.get("items") if isinstance(records_schema.get("items"), dict) else {}
    records_item_props = records_item.get("properties") if isinstance(records_item.get("properties"), dict) else {}
    graph_schema = output_props.get("spatial_graph") if isinstance(output_props.get("spatial_graph"), dict) else {}
    graph_required = graph_schema.get("required") if isinstance(graph_schema.get("required"), list) else []

    assert "addresses" in (input_schema.get("properties") or {})
    assert "records" in output_props
    assert "spatial_graph" in output_props
    assert "normalization" in records_item_props
    assert "entity_parsing" in records_item_props
    assert "address_validation" in records_item_props
    for field in ["nodes", "edges", "metrics", "failed_row_refs", "build_status"]:
        assert field in graph_required

    execution_plan = config.get("execution_plan") if isinstance(config.get("execution_plan"), dict) else {}
    gates = execution_plan.get("gates") if isinstance(execution_plan.get("gates"), dict) else {}
    assert "confirm_generate" in gates
    assert "confirm_dryrun_result" in gates
    assert "confirm_publish" in gates
    scripts = config.get("scripts") if isinstance(config.get("scripts"), list) else []
    assert len(scripts) >= 1


def test_runtime_observability_web_e2e_visual_full_lifecycle_delivery(page, base_url, tmp_path):
    if os.getenv("RUN_REAL_LLM_WEB_E2E", "0") != "1":
        pytest.skip("set RUN_REAL_LLM_WEB_E2E=1 to run real long LLM web e2e")

    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    user_rows = page.locator("#chatLog .chat-row.user")
    agent_rows = page.locator("#chatLog .chat-row.agent")
    wp_selector = page.get_by_test_id("wp-selector")
    blueprint_config = page.get_by_test_id("workpackage-blueprint-config")

    prompts = [
        "我们要做一个地址治理工作包，请先按工厂架构上下文对齐运行约束。",
        "请对齐输入输出结构：输入 addresses[]，输出 records[] 和 spatial_graph，并给字段级定义。",
        "请列出可信数据Hub中已注册且本工作包可用的API，并给出绑定关系。",
        "如果API不足，请给缺失API建议、拉取脚本方案和Key需求。",
        "依赖对齐后，请输出可执行脚本与执行计划，并生成工作包。",
    ]
    initial_user = user_rows.count()
    initial_agent = agent_rows.count()
    for idx, prompt in enumerate(prompts, start=1):
        chat_input.fill(prompt)
        send_btn.click()
        expect(user_rows).to_have_count(initial_user + idx, timeout=LONG_MULTI_TURN_TIMEOUT_MS)
        expect(send_btn).to_be_enabled(timeout=LONG_MULTI_TURN_TIMEOUT_MS)

    # 真实 LLM 可能单轮超时，补偿重试确保产出 workpackage
    for prompt in [
        "请把上面的对齐内容收敛为一个可执行工作包，并返回 workpackage_id@version。",
        "请继续完成工作包生成，并保持自然语言回复。",
    ]:
        if re.match(r".+@.+", str(wp_selector.input_value() or "").strip()):
            break
        chat_input.fill(prompt)
        send_btn.click()
        expect(send_btn).to_be_enabled(timeout=LONG_MULTI_TURN_TIMEOUT_MS)

    expect(agent_rows.last).not_to_contain_text('{"status"', timeout=10000)
    expect(agent_rows.last).not_to_contain_text('"action"', timeout=10000)
    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=60000)
    expect(page.locator("#llmAccordion")).to_contain_text("第", timeout=60000)

    # Blueprint 可视化校验：工作包结构应在面板可见
    expect(blueprint_config).to_contain_text("workpackage", timeout=60000)
    expect(blueprint_config).to_contain_text("architecture_context", timeout=60000)
    expect(blueprint_config).to_contain_text("io_contract", timeout=60000)
    expect(blueprint_config).to_contain_text("api_plan", timeout=60000)
    expect(blueprint_config).to_contain_text("execution_plan", timeout=60000)
    expect(blueprint_config).to_contain_text("scripts", timeout=60000)

    config_raw = page.evaluate(
        "() => document.querySelector('[data-testid=\"workpackage-blueprint-config\"]')?.textContent || '{}'"
    )
    config = json.loads(config_raw)
    assert isinstance(config, dict)
    assert isinstance(config.get("workpackage"), dict)
    assert isinstance(config.get("architecture_context"), dict)
    assert isinstance((config.get("io_contract") or {}).get("input_schema"), dict)
    assert isinstance((config.get("io_contract") or {}).get("output_schema"), dict)
    assert isinstance((config.get("api_plan") or {}).get("registered_apis_used"), list)
    assert isinstance((config.get("execution_plan") or {}).get("steps"), list)
    assert isinstance(config.get("scripts"), list) and len(config.get("scripts")) >= 1

    # 发布闭环：人工门禁动作
    page.locator("#actGenerate").click()
    page.locator("#actDryrun").click()
    page.locator("#actPublish").click()
    expect(page.get_by_test_id("confirm-timeline-panel")).to_contain_text("confirm_publish", timeout=10000)

    # 执行闭环：上传 10 条地址，触发治理执行
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
    csv_path = tmp_path / "runtime_addresses_full_lifecycle_10.csv"
    csv_path.write_text("\n".join(csv_lines), encoding="utf-8")
    page.locator("#sourceFile").set_input_files(str(csv_path))
    csv_input = page.get_by_test_id("csv-upload-input")
    csv_value = page.evaluate("() => document.querySelector('[data-testid=\"csv-upload-input\"]')?.value || ''")
    if "上海市徐汇区肇嘉浜路111号" not in csv_value:
        csv_input.fill("\n".join(csv_lines[1:]))
    expect(csv_input).to_have_value(re.compile(r".*上海市徐汇区肇嘉浜路111号.*", re.S), timeout=10000)

    page.get_by_test_id("upload-exec-button").click()

    # 观测与验证：records + spatial_graph + receipt + 下载
    expect(page.get_by_test_id("runtime-receipt-id")).not_to_have_text("-", timeout=120000)
    expect(page.get_by_test_id("dryrun-records-table")).to_contain_text("normalization", timeout=120000)
    expect(page.get_by_test_id("dryrun-records-table")).to_contain_text("entity_parsing", timeout=120000)
    expect(page.get_by_test_id("dryrun-records-table")).to_contain_text("address_validation", timeout=120000)
    expect(page.get_by_test_id("dryrun-graph-card")).to_contain_text("nodes=", timeout=120000)
    expect(page.get_by_test_id("dryrun-graph-card")).to_contain_text("edges=", timeout=120000)
    expect(page.get_by_test_id("dryrun-graph-card")).to_contain_text("build_status=", timeout=120000)

    expect(page.get_by_test_id("event-view-mode-toggle")).to_be_visible(timeout=30000)
    expect(page.get_by_test_id("events-table")).to_be_visible(timeout=30000)

    download_link = page.get_by_test_id("runtime-output-download-link")
    expect(download_link).to_be_visible(timeout=120000)
    href = (download_link.get_attribute("href") or "").strip()
    assert href.startswith("/output/")
    dl_resp = page.request.get(f"{base_url}{href}")
    assert dl_resp.ok


def test_runtime_observability_web_e2e_user_only_goal_nanobot_guided_full_flow(page, base_url, tmp_path):
    if os.getenv("RUN_REAL_LLM_WEB_E2E", "0") != "1":
        pytest.skip("set RUN_REAL_LLM_WEB_E2E=1 to run real long LLM web e2e")

    page.goto(
        f"{base_url}/v1/governance/observability/runtime/view?window=24h",
        wait_until="domcontentloaded",
        timeout=90000,
    )

    chat_input = page.get_by_test_id("agent-chat-input")
    send_btn = page.get_by_test_id("agent-chat-send")
    user_rows = page.locator("#chatLog .chat-row.user")
    agent_rows = page.locator("#chatLog .chat-row.agent")
    wp_selector = page.get_by_test_id("wp-selector")
    blueprint_config = page.get_by_test_id("workpackage-blueprint-config")

    fixture_path = Path(__file__).resolve().parent / "fixtures" / "address_governance_user_only_dialogue_v1.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    prompts = [str(x) for x in (payload.get("prompts") or []) if str(x).strip()]
    recovery_prompts = [str(x) for x in (payload.get("recovery_prompts") or []) if str(x).strip()]
    assert len(prompts) >= 5
    # 等待初始化完成后再记录初始值，避免把页面默认填充误判为“新生成工作包”。
    page.wait_for_timeout(1200)
    initial_wp_ref = str(wp_selector.input_value() or "").strip()

    initial_user = user_rows.count()
    initial_agent = agent_rows.count()
    for idx, prompt in enumerate(prompts, start=1):
        chat_input.fill(prompt)
        send_btn.click()
        expect(user_rows).to_have_count(initial_user + idx, timeout=LONG_MULTI_TURN_TIMEOUT_MS)
        expect(agent_rows).to_have_count(initial_agent + idx, timeout=LONG_MULTI_TURN_TIMEOUT_MS)

    for prompt in recovery_prompts:
        if re.match(r".+@.+", str(wp_selector.input_value() or "").strip()):
            break
        chat_input.fill(prompt)
        send_btn.click()
        expect(send_btn).to_be_enabled(timeout=LONG_MULTI_TURN_TIMEOUT_MS)

    # 强制触发工作包生成，直到可观测到 nanobot ↔ opencode 轨迹。
    force_generate_prompts = [
        "请立即执行 generate_workpackage，并调用 opencode 构建可执行工件，返回新的 workpackage_id@version。",
        "继续推进：必须调用 opencode，生成 entrypoint/scripts/observability，并返回新的 workpackage_id@version。",
        "请只做一件事：新建并生成可执行工作包，确保 nanobot-opencode 轨迹可见。",
    ]
    max_force_attempts = int(os.getenv("WEB_E2E_FORCE_GENERATE_ATTEMPTS", "8"))
    for i in range(max_force_attempts):
        panel_text = page.get_by_test_id("nanobot-opencode-panel").inner_text(timeout=5000)
        current_ref = str(wp_selector.input_value() or "").strip()
        if "暂无 nanobot/opencode 轨迹" not in panel_text and re.match(r".+@.+", current_ref):
            break
        prompt = force_generate_prompts[i % len(force_generate_prompts)]
        chat_input.fill(prompt)
        send_btn.click()
        expect(send_btn).to_be_enabled(timeout=LONG_MULTI_TURN_TIMEOUT_MS)

    # 聊天气泡应该保持自然语言，不渲染结构化JSON
    expect(agent_rows.last).not_to_contain_text('{"status"', timeout=15000)
    expect(agent_rows.last).not_to_contain_text('"action"', timeout=15000)
    expect(wp_selector).to_have_value(re.compile(r".+@.+"), timeout=90000)
    new_wp_ref = str(wp_selector.input_value() or "").strip()
    assert new_wp_ref
    opencode_text = page.get_by_test_id("nanobot-opencode-panel").inner_text(timeout=10000)
    assert "暂无 nanobot/opencode 轨迹" not in opencode_text

    # nanobot轨迹必须可观测（客户端<->nanobot、nanobot<->opencode）
    expect(page.get_by_test_id("nanobot-client-panel")).not_to_contain_text("暂无客户端/nanobot轨迹", timeout=45000)
    expect(page.get_by_test_id("nanobot-opencode-panel")).not_to_contain_text("暂无 nanobot/opencode 轨迹", timeout=45000)

    wp_ref = str(wp_selector.input_value() or "").strip()
    wp_bundle = Path(__file__).resolve().parents[2] / "workpackages" / "bundles" / wp_ref.replace("@", "-")
    assert wp_bundle.exists()
    assert (wp_bundle / "workpackage.json").exists()
    skills_dir = wp_bundle / "skills"
    assert skills_dir.exists()
    assert len(list(skills_dir.glob("*.md"))) >= 1

    # 工作包结构可视化
    expect(blueprint_config).to_contain_text("workpackage", timeout=90000)
    expect(blueprint_config).to_contain_text("architecture_context", timeout=90000)
    expect(blueprint_config).to_contain_text("io_contract", timeout=90000)
    expect(blueprint_config).to_contain_text("api_plan", timeout=90000)
    expect(blueprint_config).to_contain_text("execution_plan", timeout=90000)
    expect(blueprint_config).to_contain_text("scripts", timeout=90000)

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
    csv_path = tmp_path / "runtime_user_only_guided_10.csv"
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

    download_link = page.get_by_test_id("runtime-output-download-link")
    expect(download_link).to_be_visible(timeout=120000)
    href = (download_link.get_attribute("href") or "").strip()
    assert href.startswith("/output/")
    dl_resp = page.request.get(f"{base_url}{href}")
    assert dl_resp.ok

    # runtime API trace log should capture agent-chat and CRUD/runtime operations for debugging
    trace_file = Path(__file__).resolve().parents[2] / "output" / "runtime_traces" / "runtime_api_trace.jsonl"
    assert trace_file.exists()
    trace_lines = [json.loads(x) for x in trace_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert any(str((x.get("event_type") or "")) == "runtime_agent_chat" for x in trace_lines)
