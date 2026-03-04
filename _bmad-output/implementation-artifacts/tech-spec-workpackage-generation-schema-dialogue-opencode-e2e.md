---
title: '工作包生成协议化收敛与Web E2E闭环（Schema/对话协议/代码生成链路）'
slug: 'workpackage-generation-schema-dialogue-opencode-e2e'
created: '2026-03-03 12:09:30 +0800'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.11', 'FastAPI', 'Playwright', 'PostgreSQL', 'HTML/Bootstrap', 'JSON Schema Draft 2020-12']
files_to_modify: ['packages/factory_agent/agent.py', 'packages/factory_agent/llm_gateway.py', 'services/governance_api/app/routers/observability.py', 'web/dashboard/factory-agent-governance-prototype-v2.html', 'tests/web_e2e/test_runtime_observability_agent_chat_ui.py', 'tests/test_workpackage_schema_address_case_example.py']
code_patterns: ['FactoryAgent集中编排', 'FastAPI Router契约返回', 'Prototype页面单文件状态机', 'data-testid稳定选择器', 'schema先校验后兜底']
test_patterns: ['pytest', 'playwright sync_api', 'Given/When/Then验收断言', '无mock真实链路']
---

# Tech-Spec: 工作包生成协议化收敛与Web E2E闭环（Schema/对话协议/代码生成链路）

**Created:** 2026-03-03 12:09:30 +0800

## Overview

### Problem Statement

当前“工厂Agent-LLM-治理Runtime”链路虽已具备工作包生成能力，但关键问题仍存在：
1. 对话到工作包蓝图的协议收敛不够严格，字段虽有最小校验，但与 `workpackage_schema.v1` 的字段级语义对齐不完整。
2. Agent 与 LLM 的多轮对齐机制偏“重试+兜底”，需要升级为“持续互动收敛”，让 LLM 在反馈下逐轮修复直到通过 schema。
3. OpenCode 与 LLM 的职责边界在实现层未明确固化，导致“哪些代码应由 Agent 侧落地”可解释性不足。
4. Web E2E 需覆盖真实长链路：自然对话 -> 生成工作包 -> 上传10条地址CSV -> dryrun报告+spatial_graph -> 发布门禁与产物下载。

### Solution

在现有运行时之上引入“协议编排层 + 收敛循环 + 代码生成责任边界 + Web E2E 证据链”。具体为：
- 以 `workpackage_schema.v1` 为强约束，构建对话阶段上下文注入与字段级修复反馈机制。
- 将 LLM 输出从“一次生成”改为“多轮修复收敛”，不直接阻塞终止。
- 将 OpenCode 落盘职责显式化（模板/脚本/测试/集成改造由 Agent 侧完成，LLM 负责语义与策略建议）。
- 通过 Playwright 纯 Web 测试验证完整链路与可视化透明度。

### Scope

**In Scope:**
- workpackage_schema 对话注入协议（上下文、I/O契约、API计划、脚本计划）
- Agent 侧 schema 校验反馈循环（持续互动，不直接终止）
- OpenCode/LLM 责任边界在代码与文档中的落实
- Web UI 对话轨迹与工作包可视化增强
- 长会话 Web E2E（含干扰对话、工作包生成、上传、dryrun、发布、下载）

**Out of Scope:**
- 新增独立前端框架或重写页面架构
- 大规模重构治理Worker执行引擎
- 替换当前数据库模型或迁移策略
- 非数据治理场景的通用聊天产品化

## Context for Development

### Codebase Patterns

- 后端：FastAPI 路由 + Service 层 + FactoryAgent（`packages/factory_agent/agent.py`）集中编排。
- 前端：单页原型 `web/dashboard/factory-agent-governance-prototype-v2.html`，用 `data-testid` 驱动 Playwright。
- 协议：`workpackage_schema/` 独立版本化管理（schema/templates/examples/registry/changelog）。
- 测试：`tests/web_e2e/*` 覆盖运行态页面与Agent对话链路；`services/governance_api/tests/*` 覆盖API契约。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `workpackage_schema/schemas/v1/workpackage_schema.v1.schema.json` | 工作包协议v1字段级约束（唯一结构真源） |
| `workpackage_schema/README.md` | schema与模板版本管理规则 |
| `workpackage_schema/examples/v1/address_batch_governance.workpackage_schema.v1.json` | 地址治理案例示例（输入输出映射参考） |
| `packages/factory_agent/agent.py` | 工作包生成、schema校验、API计划补齐、bundle落盘主逻辑 |
| `packages/factory_agent/llm_gateway.py` | LLM 请求组织（自然对话/蓝图模式） |
| `services/governance_api/app/routers/observability.py` | Web 运行态API入口（agent-chat/upload-batch/workpackage-blueprint） |
| `web/dashboard/factory-agent-governance-prototype-v2.html` | 运行态页面、对话轨迹、蓝图面板、上传执行交互 |
| `tests/web_e2e/test_runtime_observability_agent_chat_ui.py` | 纯 Web 长会话 E2E 与工作包可视化断言 |
| `config/trusted_data_sources.json` | 可信数据Hub已注册 API 清单（含顺丰地图多接口） |

### Technical Decisions

1. `workpackage_schema.v1` 作为蓝图输出主约束，Agent 运行时校验与反馈文案必须引用字段路径（如 `api_plan.missing_apis[0].endpoint`）。
2. schema 不通过时，不走硬终止；进入“修复轮次”直到达到轮次上限，上限后允许“受控自动补全 + 明示补全项”。
3. Agent 对 LLM 的 prompt 使用“阶段化目标”（需求澄清/契约对齐/API绑定/脚本计划）并携带 `conversation_facts`，避免只发单句导致语义漂移。
4. UI 中“人机对话区”仅显示自然语言，结构化 JSON 仅放在“工作包蓝图面板 + 交互轨迹详情”中。
5. Web E2E 必须使用真实页面交互路径（输入框、按钮、上传控件），不允许脚本直调内部函数替代。

## Implementation Plan

### Tasks

- [ ] Task 1: 固化蓝图协议输入上下文构建
  - File: `packages/factory_agent/agent.py`
  - Action: 扩展 `_build_workpackage_context`，新增 `conversation_facts`、`runtime_constraints`、`schema_reference`、`registered_api_catalog_digest`。
  - Notes: 保持与 `config/trusted_data_sources.json` 同步，避免硬编码接口名。

- [ ] Task 2: 强化 LLM 蓝图提示词为“阶段化收敛协议”
  - File: `packages/factory_agent/llm_gateway.py`
  - Action: 重写 `query_workpackage_blueprint` system prompt，定义阶段目标与必填字段；补充 schema 错误回灌格式。
  - Notes: 明确“自然对话阶段禁止强制JSON，蓝图阶段必须JSON”。

- [ ] Task 3: 实现非阻塞 schema 收敛循环
  - File: `packages/factory_agent/agent.py`
  - Action: 在 `_handle_generate_workpackage` 中实现“错误聚合 -> 修复提示 -> 重试 -> 自动补全兜底”的显式状态记录。
  - Notes: 输出 `schema_fix_rounds` 与 `autofill_applied_fields` 供 UI 展示。

- [ ] Task 4: 对齐 schema 校验器与版本化 schema 文件
  - File: `packages/factory_agent/agent.py`
  - Action: 增加基于 `workpackage_schema.v1.schema.json` 的字段检查映射，减少手写校验分叉。
  - Notes: 保留现有轻量校验作为快速失败前置。

- [ ] Task 5: 明确 OpenCode/LLM 责任边界并落盘到工作包
  - File: `packages/factory_agent/agent.py`
  - Action: 在生成的 `workpackage.json` 增加 `generation_trace`（llm_contribution/opencode_contribution）。
  - Notes: 便于审计“哪些脚本由Agent落地”。

- [ ] Task 6: UI 对话展示自然语言化与JSON分区展示
  - File: `web/dashboard/factory-agent-governance-prototype-v2.html`
  - Action: 保持 chat bubble 仅渲染自然语言；将结构化结果固定渲染到 `workpackage-blueprint-*` 与 `llmAccordion` 明细区。
  - Notes: 修复 markdown 渲染中的换行/列表可读性。

- [ ] Task 7: 增强蓝图面板的可视化结构
  - File: `web/dashboard/factory-agent-governance-prototype-v2.html`
  - Action: 增加 schema 关键段落折叠（architecture_context/io_contract/api_plan/execution_plan/scripts）。
  - Notes: 兼容现有 `data-testid`，不改已有ID。

- [ ] Task 8: 补充后端Agent对话接口的链路元数据
  - File: `services/governance_api/app/routers/observability.py`
  - Action: 在 `runtime_agent_chat` 返回中透传 `schema_fix_rounds`、`workpackage_blueprint_summary`。
  - Notes: 仅追加字段，保持向后兼容。

- [ ] Task 9: 扩展纯Web长会话E2E用例（地址治理case）
  - File: `tests/web_e2e/test_runtime_observability_agent_chat_ui.py`
  - Action: 新增用例，覆盖“架构上下文/IO契约/API绑定/缺失API建议与脚本/执行计划”五段式对话确认。
  - Notes: 对话轮次不设上限到发布前，至少包含干扰对话并验证回归治理主题。

- [ ] Task 10: 补充上传10条地址CSV后端到前端产物断言
  - File: `tests/web_e2e/test_runtime_observability_agent_chat_ui.py`
  - Action: 断言 `records[]` 三段结果 + `spatial_graph` 核心字段 + 下载链接可访问。
  - Notes: 用真实 `upload-batch` 路径，不允许 mock。

- [ ] Task 11: 增加协议回归单测
  - File: `tests/test_workpackage_schema_address_case_example.py`
  - Action: 新增字段级断言，确保地址治理case完整表达输入输出定义与API计划。
  - Notes: 与 `workpackage_schema/examples/v1` 同步。

- [ ] Task 12: 文档化交付与执行命令
  - File: `docs/testing/test_case_design_runtime_observability_e2e_cli_agent_llm_runtime_2026-03-02.md`
  - Action: 增补“真实Web链路+真实外部LLM+无fallback/mock”的执行章节与故障处理。
  - Notes: 文档保持中文。

### Acceptance Criteria

- [ ] AC 1: Given 用户在 Web 发起工作包生成请求，when Agent 进入蓝图生成阶段，then Agent->LLM 请求体必须包含 `architecture_context/io_contract/api_plan/execution_plan/scripts` 对齐目标。
- [ ] AC 2: Given LLM 首轮输出缺失 schema 字段，when Agent 校验失败，then 系统进入下一轮修复对话并提供字段级错误，不直接终止流程。
- [ ] AC 3: Given schema 在限定轮次内收敛通过，when 工作包落盘，then `workpackage.json` 可由 `workpackage_schema.v1` 解释且包含地址治理输入输出定义。
- [ ] AC 4: Given 人机对话在聊天面板展示，when 返回结构化内容，then chat bubble 显示自然语言，不直接显示 JSON 原文。
- [ ] AC 5: Given 用户打开“工作包蓝图面板”，when 工作包已生成，then 可视化展示 `workpackage/architecture_context/io_contract/api_plan/execution_plan/scripts`。
- [ ] AC 6: Given Web E2E 执行长会话到发布，when 上传10条地址CSV并执行，then dryrun 报告包含 `records[].normalization/entity_parsing/address_validation` 与 `spatial_graph.nodes/edges/metrics/failed_row_refs/build_status`。
- [ ] AC 7: Given dryrun 与发布完成，when 页面渲染产物链接，then `runtime-output-download-link` 可下载并返回 200。
- [ ] AC 8: Given 可信数据Hub已注册 API 存在，when 生成 `api_plan.registered_apis_used`，then 至少包含已注册接口ID与调用映射，不可退化为空泛字符串。
- [ ] AC 9: Given 已注册 API 不足，when LLM 提出扩展，then `missing_apis` 必须包含 endpoint/key需求/register_plan，且Agent生成对应脚本骨架。
- [ ] AC 10: Given 回归测试执行，when RUN_REAL_LLM_WEB_E2E=1，then 用例走纯 Web 交互链路并产出可追溯证据文件。

## Additional Context

### Dependencies

- 外部 LLM API（真实网络调用，模型 `gpt-5.3-codex`）
- PostgreSQL（Docker 实例，禁 fallback 到本机 PG）
- 可信数据Hub配置：`config/trusted_data_sources.json`
- Playwright 浏览器依赖（headed 模式用于可视化）

### Testing Strategy

- 单元测试：
  - FactoryAgent schema 收敛循环、蓝图字段对齐、API计划补齐逻辑。
- API 契约测试：
  - `runtime/agent-chat`、`runtime/workpackage-blueprint`、`runtime/upload-batch` 返回结构。
- Web E2E（核心）：
  - 纯页面交互长会话 -> 生成工作包 -> 上传CSV -> dryrun -> 发布 -> 下载。
  - 断言 `data-testid` 稳定性与内容可解释性。
- 回归门禁：
  - 禁 mock/fallback；外部依赖失败必须显式报错并阻塞。

### Notes

- 高风险：外部 API 稳定性与 key 配置可能导致 E2E 波动，需要在用例中提供可诊断日志。
- 兼容性：保持现有 `data-testid` 与接口字段向后兼容，新增字段仅追加。
- 交付策略：先补失败测试，再改实现，再全量回归。

## Review Notes

- Adversarial review：已执行本次改动范围自检（协议字段、收敛轮次、API透传与UI模型渲染）。
- Findings：未发现阻断级缺陷；保留风险为“真实外部LLM长链路受外部网络与密钥状态影响”。
- Resolution approach：自动修复（按失败测试驱动完成实现并回归）。
