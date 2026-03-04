---
title: 'epic地址治理全链路可视化Web-E2E专业用例设计'
slug: 'epic-address-governance-visual-web-e2e-professional-case'
created: '2026-03-03 22:21:30 +0800'
status: 'in-progress'
stepsCompleted: [1, 2]
tech_stack: ['Python 3.11', 'FastAPI', 'Playwright (sync_api)', 'PostgreSQL + psycopg2 + SQLAlchemy', '原生 HTML/JS 可视化页面', 'JSON Schema Draft 2020-12', 'Markdown 规范文档体系(PRD/Epic/Architecture/Tech-Spec)']
files_to_modify: [
  '/Users/huda/Code/spatial-intelligence-data-factory/tests/web_e2e/test_runtime_observability_agent_chat_ui.py',
  '/Users/huda/Code/spatial-intelligence-data-factory/tests/web_e2e/conftest.py',
  '/Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/factory-agent-governance-prototype-v2.html',
  '/Users/huda/Code/spatial-intelligence-data-factory/services/governance_api/app/routers/observability.py',
  '/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/agent.py',
  '/Users/huda/Code/spatial-intelligence-data-factory/packages/factory_agent/llm_gateway.py',
  '/Users/huda/Code/spatial-intelligence-data-factory/workpackage_schema/schemas/v1/workpackage_schema.v1.schema.json',
  '/Users/huda/Code/spatial-intelligence-data-factory/workpackage_schema/examples/v1/address_batch_governance.workpackage_schema.v1.json',
  '/Users/huda/Code/spatial-intelligence-data-factory/workpackage_schema/README.md'
]
code_patterns: ['Router -> Service/Agent 编排 -> Runtime 执行链路', 'Web 页面以 data-testid 稳定驱动 E2E', '对话层自然语言展示、结构化内容在蓝图/轨迹面板展示', 'schema 版本化由 workpackage_schema/registry.json 管理', 'Ring 0: no-fallback/no-mock/no-workground 真实链路验收']
test_patterns: ['严格 TDD: 先失败测试再实现再回归', 'Pytest + Playwright 纯 Web E2E(headed 可视化)', 'API 契约与页面断言并行覆盖', '失败显式阻断，不允许伪成功']
---

# Tech-Spec: epic地址治理全链路可视化Web-E2E专业用例设计

**Created:** 2026-03-03 22:21:30 +0800

## Overview

### Problem Statement

当前缺少一条“专业、可复现、可视化”的 Web E2E 主用例，无法稳定验证以下全链路：
1. 用户与 nanobot 的多轮对话是否形成明确治理目标与验收目标。
2. nanobot 是否内置并正确使用 `workpackage_schema.v1` 知识来收敛工作包规格。
3. nanobot 是否将规格清晰传递给 opencode 并生成完整脚本集合（治理脚本 + 质检脚本）。
4. runtime 是否可执行该工作包并输出地址治理成果（records + spatial_graph + 下载工件）。
5. 界面是否完整展示对话输入、轨迹过程和结果产出。

### Solution

设计并实现一条“真实依赖、界面可见、长链路”的 Web E2E 专业主用例：
1. 先执行 preflight（PG / nanobot / opencode / LLM）硬门禁，失败即阻断用例。
2. 在测试代码中给出明确的“多轮对话输入脚本”，覆盖：治理目标、核心地址治理能力、成果表达形式、schema 约束、脚本交付要求。
3. 在页面操作中完整执行：对话 -> 工作包生成 -> 人工门禁确认 -> 上传地址集 -> runtime 执行 -> 成果验证。
4. 在断言中同时覆盖：
   - 对话与轨迹（客户端↔nanobot、nanobot↔opencode）
   - 工作包蓝图结构（含 schema 关键字段）
   - 治理输出（records / spatial_graph / runtime_receipt / 下载链接）

### Scope

**In Scope:**
- 产出一条 Epic 级专业 Web E2E 主用例（headed 可视）。
- 用例内置具体对话输入脚本与界面操作步骤。
- 用例明确校验工作包 schema 知识传递和脚本生成结果。
- 用例执行中构造地址测试数据并验证治理产出。

**Out of Scope:**
- 非 Web 交互路径（CLI/纯脚本替代）验收。
- 与地址治理无关的新业务能力拓展。

## Context for Development

### Codebase Patterns

- 文档事实源采用 `docs/` 主线（PRD/Epic/Architecture），历史规格通过 `docs/specs-fusion-report-2026-02-27.md` 与 `docs/spec-fusion-status-2026-02-27.yaml` 融合映射，避免双轨漂移。
- 产品级目标由 PRD 定义（`docs/prd-spatial-intelligence-data-factory-2026-02-28.md`），Epic 级运行态目标由 `docs/epic-runtime-observability-v2-2026-02-28.md` 约束到 runtime 可观测与 no-fallback 主链路。
- 工作包协议采用独立版本化目录 `workpackage_schema/`，通过 `registry.json` 作为唯一版本入口；`schemas/templates/examples` 必须同版本配套。
- `workpackage_schema.v1` 定义了最小闭环字段：`workpackage/architecture_context/io_contract/api_plan/execution_plan/scripts/skills`，并规定 schema mismatch 的处理为“持续互动修复”。
- E2E 主链路基于运行态页面入口 `/v1/governance/observability/runtime/view` 与稳定 testid；核心流程为“对话 -> 生成 -> 门禁 -> 上传 -> 试运行 -> 发布 -> 结果可视化/下载”。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| /Users/huda/Code/spatial-intelligence-data-factory/tests/web_e2e/test_runtime_observability_agent_chat_ui.py | E2E 主用例落地 |
| /Users/huda/Code/spatial-intelligence-data-factory/tests/web_e2e/conftest.py | preflight 与运行前门禁 |
| /Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/factory-agent-governance-prototype-v2.html | 页面交互与 data-testid |
| /Users/huda/Code/spatial-intelligence-data-factory/workpackage_schema/schemas/v1/workpackage_schema.v1.schema.json | 工作包 schema 契约 |
| /Users/huda/Code/spatial-intelligence-data-factory/docs/prd-spatial-intelligence-data-factory-2026-02-28.md | 产品级目标、范围与非功能基线 |
| /Users/huda/Code/spatial-intelligence-data-factory/docs/epic-runtime-observability-v2-2026-02-28.md | Epic 范围、门禁、分层 DoD、风险 |
| /Users/huda/Code/spatial-intelligence-data-factory/docs/specs-fusion-report-2026-02-27.md | 历史 specs 与当前主线融合规则 |
| /Users/huda/Code/spatial-intelligence-data-factory/docs/architecture/workpackage-schema-address-governance-case-v1-2026-03-03.md | 地址治理案例的 schema 字段映射 |
| /Users/huda/Code/spatial-intelligence-data-factory/workpackage_schema/README.md | schema 版本管理与配套模板强制规则 |
| /Users/huda/Code/spatial-intelligence-data-factory/_bmad-output/implementation-artifacts/tech-spec-workpackage-generation-schema-dialogue-opencode-e2e.md | 既有相关技术方案与实现边界基线 |

### Technical Decisions

- 本次 E2E 规格以 PRD/Epic 目标为上位约束，以 `workpackage_schema.v1` 为工作包字段真源；测试输入脚本必须显式覆盖 schema 六大块（工作包元信息、架构上下文、I/O 契约、API 计划、执行计划、脚本计划）。
- Web 交互日志必须区分三层可观测对象：用户↔FactoryAgent、客户端↔nanobot、nanobot↔opencode；对话区展示自然语言，结构化对象仅在蓝图/轨迹区域展示。
- 运行门禁前置：启动前自检应覆盖 PostgreSQL、nanobot、opencode 及 LLM 连通性，任一失败则阻断 E2E（符合 no-fallback/no-mock）。
- 测试设计采用“高价值主线 + 可诊断断言”：优先确保工作包开发、发布、治理执行、结果校验完整跑通，并在失败时可定位到具体链路段。

## Implementation Plan

### Tasks

- 待 Step 2 深入调查后补全为可执行任务分解。

### Acceptance Criteria

- 待 Step 2 深入调查后补全 Given/When/Then。

## Additional Context

### Dependencies

- PostgreSQL(docker)
- nanobot (FactoryAgent)
- opencode
- 外部 LLM 网关
- Playwright headed 环境

### Testing Strategy

- 先失败用例：对话脚本完整性 + 可视化流程断言 + 产出断言。
- 再实现与修复。
- 回归：E2E headed 主用例 + 相关 API/UI 合同测试。

### Notes

- 用户重点关注：用例中的“具体对话输入脚本”与“界面操作过程”。
