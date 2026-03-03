from __future__ import annotations

import os
import re

from playwright import sync_api
import pytest

expect = sync_api.expect


def test_runtime_observability_manual_agent_chat_panel(page, base_url):
    page.goto(f"{base_url}/v1/governance/observability/runtime/view?window=24h", wait_until="domcontentloaded")
    expect(page.get_by_test_id("agent-chat-panel")).to_be_visible()
    expect(page.get_by_test_id("agent-chat-input")).to_be_visible()
    expect(page.get_by_test_id("agent-chat-send")).to_be_visible()
    expect(page.get_by_test_id("agent-chat-log")).to_be_visible()
    expect(page.locator("#llmAccordion")).to_be_visible()
    expect(page.locator("#wpMaintLogs")).to_be_visible()
    expect(page.locator("#actGenerate")).to_be_visible()
    expect(page.locator("#actDryrun")).to_be_visible()
    expect(page.locator("#actPublish")).to_be_visible()

    page.get_by_test_id("agent-chat-input").fill("列出工作包")
    page.get_by_test_id("agent-chat-send").click()
    expect(page.get_by_test_id("agent-chat-log")).to_contain_text("列出工作包", timeout=30000)
    expect(page.locator("#llmAccordion")).to_contain_text("第 1 轮", timeout=30000)

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
        "你好，先介绍你能做什么。",
        "我想做数据治理，先帮我理一下目标。",
        "补充约束：数据量不超过100条。",
        "另外预算有限，优先低成本方案。",
        "今天天气如何？",
        "不聊天气了，回到治理方案。",
        "我们有地址字段、商户名、手机号，先做什么？",
        "请给我一个最小可执行步骤。",
        "干扰一下：推荐一首歌。",
        "继续，给我质量规则清单。",
        "规则里增加重复值、空值、格式异常。",
        "再加上地址标准化和实体拆分。",
        "给我一个可回滚策略。",
        "如果校验失败，如何人工介入？",
        "请说明 dry run 的验收点。",
        "我希望能追踪每轮与LLM交互。",
        "再补充：输出尽量中文、简洁。",
        "现在请基于以上内容创建工作包，目标是地址验真、标准化、实体拆分、空间图谱。",
        "把工作包目标再复述一遍。",
        "确认：我们按这个工作包执行。",
        "最后列出当前工作包。",
    ]

    initial_agent_count = agent_rows.count()
    initial_user_count = user_rows.count()

    for total_turns, turn in enumerate(dialogue_rounds, start=1):
        chat_input.fill(turn)
        send_btn.click()
        expect(user_rows).to_have_count(initial_user_count + total_turns, timeout=45000)
        expect(agent_rows).to_have_count(initial_agent_count + total_turns, timeout=45000)

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
    expect(page.get_by_test_id("csv-upload-input")).to_contain_text("上海市徐汇区肇嘉浜路111号", timeout=10000)

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
