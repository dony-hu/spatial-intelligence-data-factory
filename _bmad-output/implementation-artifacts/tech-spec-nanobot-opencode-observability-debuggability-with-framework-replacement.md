---
title: 'nanobot-opencode-真实执行轨迹可测试性与可调试性增强（含框架替换）'
slug: 'nanobot-opencode-observability-debuggability-with-framework-replacement'
created: '2026-03-03 17:59:07 +0800'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - 'Python 3.11'
  - 'FastAPI + TestClient (services/governance_api)'
  - '静态前端 HTML/JS + Bootstrap 5 (web/dashboard)'
  - 'pytest + Playwright (headed Web E2E)'
  - 'FactoryAgent/nanobot 编排 + OpenCode 构建器 + 外部 LLM 网关'
files_to_modify:
  - '/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/agent.py'
  - '/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/routing.py'
  - '/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/opencode_workpackage_builder.py'
  - '/Users/huda/Code/spatial-intelligence-data-factory/services/governance_api/app/routers/observability.py'
  - '/Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/factory-agent-governance-prototype-v2.html'
  - '/Users/huda/Code/spatial-intelligence-data-factory/tests/web_e2e/test_runtime_observability_agent_chat_ui.py'
  - '/Users/huda/Code/spatial-intelligence-data-factory/services/governance_api/tests/test_runtime_agent_chat_api.py'
  - '/Users/huda/Code/spatial-intelligence-data-factory/tests/test_nanobot_opencode_parallel_panels_ui.py'
code_patterns:
  - 'runtime/agent-chat 端点聚合 Agent 结果，并在路由层拼装 trace item'
  - 'trace 会话当前保存在 _AGENT_TRACE_SESSIONS 内存字典，返回窗口为最近 30 条'
  - 'FactoryAgent 中仍包含 _run_workpackage_blueprint_query 及 LLM 驱动蓝图生成逻辑'
  - 'OpenCodeWorkpackageBuilder 负责落盘 workpackage.json/脚本/观测工件'
  - 'UI 通过 toNaturalChatReply 将结构化结果转换为自然语言展示'
  - '当前 nanobot↔opencode 轨迹在路由层按 action=generate_workpackage 合成，非真实执行事件流'
test_patterns:
  - '后端 API 合同测试：TestClient + pytest（支持真实 LLM gate 开关）'
  - '前端结构测试：HTML 静态断言 data-testid 与面板布局'
  - 'Web E2E：Playwright 多轮对话 + 工作包生成/发布/上传/干运行断言'
  - 'TDD 顺序强制：先补失败测试，再实现，再回归'
---

# Tech-Spec: nanobot-opencode-真实执行轨迹可测试性与可调试性增强（含框架替换）

**Created:** 2026-03-03 17:59:07 +0800

## Overview

### Problem Statement

当前测试程序与系统对话时，虽然已有基础轨迹面板，但仍不足以支撑真实排障与可测试验证：
1. 无法稳定看到从客户端到 nanobot，再到 opencode 的完整执行语义与步骤。
2. 缺少用于故障复盘的日志文件证据（仅页面态不足）。
3. 现有链路未覆盖“工作包开发→发布→治理执行→结果验证”的一体化可视验收。
4. 若不纳入 nanobot 框架替换/重构，story 目标无法跑通。

### Solution

在不使用 mock/fallback 的前提下，设计并实现“真实执行轨迹可观测”方案：
1. 将 nanobot 框架替换纳入主方案，统一作为工厂 Agent 编排核心。
2. 建立双层可观测输出：
   - Web 面板实时轨迹（客户端↔nanobot、nanobot↔opencode 并列面板）
   - 文件日志落地（用于复盘和定位）
3. 构建单条可视化 Web E2E 长链路，覆盖：工作包开发、发布、治理执行与结果验收（含工作包内容与数据治理成果可见）。

### Scope

**In Scope:**
- nanobot 框架替换/重构方案纳入实现范围。
- 真实链路轨迹采集与展示（客户端↔nanobot、nanobot↔opencode）。
- 轨迹日志文件化输出（非数据库持久化）。
- 工作包内容可视化与治理成果可视化增强。
- Headed Web E2E：完整链路可观测验收。

**Out of Scope:**
- 轨迹数据库持久化与历史检索系统。
- 原始 payload 细节展示（明确不需要）。
- 与当前目标无关的业务领域能力扩展。

## Context for Development

### Codebase Patterns

- API 入口集中在 `services/governance_api/app/routers/observability.py`，`/v1/governance/observability/runtime/agent-chat` 当前负责调用 `FactoryAgent.converse()`，并在路由层写入 `client_nanobot/nanobot_opencode` 轨迹。
- `packages/factory_agent/agent.py` 是当前核心编排器：意图识别、LLM 调用、工作包蓝图归一化和校验、调用 OpenCode 构建器落盘。
- `packages/factory_agent/routing.py` 以关键词规则做意图分发；`generate_workpackage` 是触发蓝图→工件生成的关键入口。
- `packages/factory_agent/opencode_workpackage_builder.py` 承担文件工件生成，但未输出“可调试执行日志文件”这一统一规范。
- 前端 `web/dashboard/factory-agent-governance-prototype-v2.html` 已有并列双面板（客户端↔nanobot、nanobot↔opencode），但展示内容主要来自后端返回对象，尚缺真实步骤级事件语义。
- `project-context.md` 未发现，约束以仓库 `AGENTS.md` 和现有 story/spec 文档为准。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| /Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/agent.py | FactoryAgent 主流程；现有蓝图生成/校验/OpenCode 调用与发布执行逻辑 |
| /Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/routing.py | 对话意图识别（决定是否触发工作包生成/发布） |
| /Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/opencode_workpackage_builder.py | 工作包工件落盘；后续需接入真实执行日志规范 |
| /Users/huda/Code/spatial-intelligence-data-factory/services/governance_api/app/routers/observability.py | Agent 聊天接口、轨迹返回与执行流程编排 |
| /Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/factory-agent-governance-prototype-v2.html | 可视化面板与对话/轨迹渲染 |
| /Users/huda/Code/spatial-intelligence-data-factory/tests/web_e2e/test_runtime_observability_agent_chat_ui.py | Web E2E 场景定义与断言 |
| /Users/huda/Code/spatial-intelligence-data-factory/services/governance_api/tests/test_runtime_agent_chat_api.py | API 合同测试、轨迹字段回归 |
| /Users/huda/Code/spatial-intelligence-data-factory/tests/test_nanobot_opencode_parallel_panels_ui.py | 双面板并列结构契约测试 |

### Technical Decisions

- 决策1：将“nanobot 框架替换”纳入改造范围；`FactoryAgent` 只做工厂编排，不再在路由层伪造 opencode 过程语义。
- 决策2：轨迹落地采用“双通道”：UI 实时返回 + 文件日志（JSONL/按 session 切分）；明确不做 DB 持久化。
- 决策3：去除“LLM 输出直接生成可执行工具包”的强耦合，改为 nanobot 分解任务，opencode 生成工件；LLM提供分析/规划能力。
- 决策4：Web 面板必须可见三类结果：对话轨迹、工作包结构、治理执行成果（records/spatial_graph/下载链接）。
- 决策5：坚持 Ring 0：真实外部链路、no-mock、no-fallback、no-workground。

## Implementation Plan

### Tasks

- [ ] Task 1: 收敛 nanobot 框架替换边界，移除路由层伪造 opencode 轨迹的职责
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/services/governance_api/app/routers/observability.py`
  - Action: 将 `runtime/agent-chat` 从“按 action 拼装轨迹”改为“消费 FactoryAgent 返回的真实 trace events”；仅保留 API 协议聚合与错误处理。
  - Notes: 保持接口兼容字段 `nanobot_traces.client_nanobot/nanobot_opencode`，但数据来源必须是 agent 真实执行过程。

- [ ] Task 2: 在 FactoryAgent 内引入统一 trace event 总线与日志文件落地
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/agent.py`
  - Action: 增加会话级 trace collector（包含 `session_id/trace_id/channel/direction/stage/event_type/content/status/ts`），并将事件按 JSONL 写入 `output/runtime_traces/{session_id}.jsonl`。
  - Notes: 不做 DB 持久化；每次请求结束返回最近窗口（如 30 条）供 UI 即时展示。

- [ ] Task 3: 调整 FactoryAgent 生成链路职责，强调“nanobot 编排 + opencode 产物生成”
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/agent.py`
  - Action: 让 LLM 仅承担分析规划（上下文对齐/约束建议），工作包工件生成由 nanobot 调 opencode builder 完成；轨迹中需清晰记录 nanobot→opencode 的任务下发与回执。
  - Notes: 与 `query_workpackage_blueprint` 弱耦合，避免让 LLM直接输出最终可执行工件文本。

- [ ] Task 4: 扩展 OpenCode 构建器输出调试证据
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/opencode_workpackage_builder.py`
  - Action: 增加构建阶段日志/metadata 产物（例如 `observability/opencode_build_report.json`），并在返回轨迹中附 `artifacts` 路径。
  - Notes: 便于定位“生成失败/脚本不完整/依赖缺失”问题。

- [ ] Task 5: 优化前端双面板展示语义（真实过程优先）
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/factory-agent-governance-prototype-v2.html`
  - Action: 双面板继续并列显示，不改 tab；增强每条日志的 stage/event/status/时间与工件链接展示；对话气泡保持自然语言，不回显 JSON 噪声。
  - Notes: 保持现有 data-testid 稳定，避免破坏既有自动化。

- [ ] Task 6: 增加/调整 API 合同测试（先写失败用例）
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/services/governance_api/tests/test_runtime_agent_chat_api.py`
  - Action: 新增断言：轨迹来自 agent 真实事件、响应包含日志文件路径或日志标识、生成工作包后有 nanobot/opencode 双向事件。
  - Notes: 测试中允许 stub agent，但不得在产品代码中引入 mock/fallback 逻辑绕行真实链路。

- [ ] Task 7: 增加/调整前端结构与 E2E 测试（先写失败用例）
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/tests/test_nanobot_opencode_parallel_panels_ui.py`
  - Action: 断言并列面板持续存在，且新增字段渲染位（状态、工件、时间）存在。
  - Notes: 防止后续 UI 回退为简化展示。

- [ ] Task 8: 完善真实 Web 长链路 E2E 验收
  - File: `/Users/huda/Code/spatial-intelligence-data-factory/tests/web_e2e/test_runtime_observability_agent_chat_ui.py`
  - Action: 增强 headed 用例断言，覆盖“工作包开发→发布→治理执行→验证”，并明确校验：
    - 双面板均出现有效轨迹
    - 工作包内容面板可见
    - 治理成果可见（records + spatial_graph）
    - 下载链接可访问
  - Notes: 仅走 Web 直接交互，不退化为脚本集成测试。

### Acceptance Criteria

- [ ] AC 1: Given 用户在运行态页面发起工作包创建请求，when 请求由 `runtime/agent-chat` 处理，then 返回中 `nanobot_traces` 必须包含 `client_nanobot` 与 `nanobot_opencode` 两路真实事件，且每条事件包含 `stage/event_type/status/ts`。
- [ ] AC 2: Given 工厂 Agent 完成一次会话编排，when 会话结束，then 系统在 `output/runtime_traces/` 生成对应会话日志文件（JSONL），可用于复盘。
- [ ] AC 3: Given nanobot 调用 opencode 生成工件，when 构建完成，then 轨迹中可看到 nanobot->opencode 下发事件与 opencode->nanobot 回执事件，且回执含工件路径。
- [ ] AC 4: Given 用户查看运行态页面双面板，when 有执行轨迹，then 左侧面板展示客户端↔nanobot，右侧面板展示 nanobot↔opencode，且无 tab 切换依赖。
- [ ] AC 5: Given 用户进行完整流程（创建工作包→确认发布→上传10条地址执行），when 流程完成，then 页面可见工作包结构信息、records 表格（normalization/entity_parsing/address_validation）与 spatial_graph 摘要（nodes/edges/build_status）。
- [ ] AC 6: Given 执行完成且存在输出工件，when 用户点击下载链接，then 返回 200 且可获取输出文件。
- [ ] AC 7: Given 对话区展示 Agent 回复，when 返回结构化对象，then UI 应转换为自然语言回复，不直接显示原始 JSON 文本。
- [ ] AC 8: Given 真实链路配置（no-mock/no-fallback/no-workground），when 任一外部依赖不可用，then 系统明确报错并保留可追溯轨迹，不得伪造成功。

## Additional Context

### Dependencies

- nanobot 运行框架（作为工厂 Agent 编排执行体）
- opencode CLI/运行时（用于代码与工件生成）
- 外部 LLM 网关（真实调用）
- governance_api 服务可用
- Playwright 浏览器驱动与 pytest 执行环境
- 文件系统写权限（`output/runtime_traces`、`workpackages/bundles`）

### Testing Strategy

- TDD 强制流程：
  1) 先补失败测试：`test_runtime_agent_chat_api.py`、`test_nanobot_opencode_parallel_panels_ui.py`、`test_runtime_observability_agent_chat_ui.py`。
  2) 再实现：FactoryAgent trace collector + 路由聚合改造 + UI 渲染增强。
  3) 最后回归：后端单测 + 前端结构测试 + headed Web E2E 长链路。
- E2E 口径：
  - 必须是“纯 Web 直接交互”
  - 必须观察到双面板轨迹、工作包内容、治理成果与下载工件。

### Notes

- 用户已确认：不需要 payload 原文展示；必须看到治理成果与工作包内容；日志需文件化留证。
- 高风险点：
  - `agent.py` 体量大（>1700 行），重构时易引入行为回归，需要最小步提交并强化回归测试。
  - 真实外部依赖（LLM/opencode）可能有超时或环境不一致，测试需给出清晰失败证据。
- 已知限制：
  - 本期不做轨迹入库与跨会话检索，仅做文件证据与页面可视化。
