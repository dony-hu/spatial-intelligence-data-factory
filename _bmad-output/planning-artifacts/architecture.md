---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - docs/product-brief-spatial-intelligence-data-factory-2026-02-28.md
  - docs/prd-spatial-intelligence-data-factory-2026-02-28.md
  - docs/prd-runtime-observability-dashboard-2026-02-28.md
  - docs/ux-runtime-observability-s2-15-page-design-2026-03-02.md
  - docs/ux-obs-runtime-s2-15-human-loop-e2e-2026-03-02.md
  - docs/architecture-spatial-intelligence-data-factory-2026-02-28.md
  - docs/architecture/模块边界.md
  - docs/architecture/workpackage-schema-address-governance-case-v1-2026-03-03.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-03-03'
project_name: 'spatial-intelligence-data-factory'
user_name: 'huda'
date: '2026-03-03'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._


## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
项目需要同时满足“工厂侧需求确认与工作包生成发布”与“运行态可观测闭环”两条主链路。核心功能包括：
1. 按 `workpackage_id@version` 执行上传批次并获取 Runtime 回执；
2. 完整展示确认门禁链路（`confirm_generate / confirm_dryrun_result / confirm_publish`）；
3. 产出并展示 dry-run 报告（`records + spatial_graph`）；
4. 支持 `CLI / Agent / LLM / Runtime` 事件时间线下钻；
5. 保持 `workpackage_schema` 协议版本化与 `skills` 作为工作包组成部分。

**Non-Functional Requirements:**
1. No-Fallback / No-Mock（关键链路失败必须阻断并暴露真实错误）；
2. 全链路可审计（事件、确认动作、回执可追溯）；
3. 契约优先（schema 版本路由、门禁校验）；
4. PG-only 持久化一致性；
5. 运行态可观测查询可用性与可解释性（中文可读字段 + JSON 原文）；
6. 业务无感迁移（迁移阶段用户侧执行体验、阻断语义、回溯能力保持一致）。

**Scale & Complexity:**
项目属于高复杂度架构演进：既有系统持续交付中进行编排内核替换，且需保持外部行为一致。

- Primary domain: Agent orchestration + backend governance services + runtime observability
- Complexity level: High (Migration-Critical)
- Estimated architectural components: 10-14（入口、编排、网关、工作流、持久化、观测、门禁、契约管理、运行时执行、审计）

### Technical Constraints & Dependencies

1. 现有外部契约不可破坏：`factory_cli`、`governance_api`、runtime publish/receipt 链路；
2. `workpackage_schema` 为项目一级目录入口，必须通过 `registry.json` 路由；
3. `skills` 已进入 schema 强约束，生成/发布流程必须携带并可解析；
4. 运行链路依赖真实 LLM 与 PG，不能通过 fallback/workaround 伪成功；
5. 可观测 API 与 UI 测试（含 E2E）是验收主门槛之一。

**迁移边界矩阵：**
- 保持不变：`factory_cli` 对外调用面、`governance_api` 契约、`workpackage_schema` 产物格式。
- 可替换：`factory_agent` 内部编排状态推进与工具调度内核。
- 禁止变更：门禁语义（确认动作）、阻断语义与错误码、关键事件字段语义。

**迁移发布策略（不回退）：**
- 采用单轨切换到 nanobot，不保留 legacy 编排回退路径；
- 若切换门槛未满足，执行 No-Go 延期，不执行技术回滚；
- 切换后进入高强度观测值守窗口，按审计与事件证据判定稳定性。

### Cross-Cutting Concerns Identified

1. 状态机一致性：nanobot 内部状态与现有业务状态映射必须一一对应；
2. 观测一致性：事件 `source/type/status` 语义需与现有看板和 API 对齐；
3. 审计合规：确认动作、发布动作、失败动作均需留痕；
4. 契约治理：workpackage schema 版本与 bundle 结构必须持续守卫；
5. 迁移风险控制：采用“内核替换、接口保持”的渐进策略，保障回归可控；
6. 测试即架构约束：
   - 真实 LLM 链路必须可验收；
   - 事件语义一致性必须可验收；
   - `workpackage_id@version -> runtime_receipt_id` 一致性必须可验收。
7. 切换前强门禁（无回退前提）：
   - 真实链路 E2E 全通过；
   - 门禁阻断用例全通过；
   - 事件语义一致性测试全通过；
   - 回执追溯一致性测试全通过。


## Starter Template Evaluation

### Primary Technology Domain

Python 后端编排内核迁移（brownfield integration）  
基于现有 `factory_cli -> factory_agent -> governance_api/runtime` 链路，目标是替换 `factory_agent` 内部编排内核为 nanobot。

### Starter Options Considered

1. PyPI 稳定包接入（nanobot-ai）
- 优点：版本可锁定、改造面最小、便于与现有服务共存
- 缺点：需持续关注上游发布变化

2. 源码接入（git clone HKUDS/nanobot + editable install）
- 优点：可深度定制
- 缺点：维护成本高、侵入性强

3. 自建最小控制循环
- 优点：完全自主
- 缺点：偏离“迁移到 nanobot”目标，不符合当前决策

### Selected Starter: nanobot-ai (PyPI stable pinned)

**Rationale for Selection:**
在不改变外部契约前提下，PyPI 稳定包能最快形成可控迁移基线，适合“单轨切换 + 强门禁发布”的策略。

**Initialization Command:**

```bash
python -m pip install "nanobot-ai==0.1.4.post3"
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Python 3.11+（与当前项目主运行时一致）

**Integration Pattern:**
- 通过 `packages/factory_agent/nanobot_adapter.py` 封装接入
- 仅替换 `factory_agent` 内部编排，不修改 CLI/API 外部契约

**Build & Dependency Policy:**
- 锁定 nanobot 版本，升级需走专门 Story + 全量回归
- 禁止隐式升级（CI 中检查依赖漂移）

**Testing Baseline:**
- 真实 LLM 链路 E2E
- 门禁阻断语义一致性
- 事件语义一致性
- `workpackage_id@version -> runtime_receipt_id` 追溯一致性

**Note:** nanobot 接入与适配层实现应作为第一实现 Story。


## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. 编排内核单轨切换：`factory_agent` 仅保留 nanobot 路径，不保留 legacy 回退入口。
2. 迁移边界冻结：外部契约不变（CLI/API/Runtime/Observability），只替换内部编排。
3. 切换前强门禁：真实 LLM E2E、门禁阻断、事件语义一致、回执追溯一致全部通过。
4. 版本冻结策略：nanobot 迁移窗口内，禁止同步升级 FastAPI/SQLAlchemy 等底座依赖。

**Important Decisions (Shape Architecture):**
1. 适配层模式：新增 `packages/factory_agent/nanobot_adapter.py`，统一封装 `plan / execute_dryrun / submit_runtime`。
2. 事件语义标准化：保持 `source/event_type/status/pipeline_stage` 与现有 API/看板一致。
3. 工作包契约强制：`workpackage_schema` + `skills` 校验作为发布前必经门禁。

**Deferred Decisions (Post-MVP):**
1. FastAPI 等基础依赖升级到最新稳定版。
2. 进一步拆分 `factory_agent` 为更细粒度 orchestration modules。
3. 可观测平台查询优化（分层缓存、预聚合表）。

### Data Architecture

1. 数据库：保持 PostgreSQL 多 schema（governance/runtime/metadata/...）单主路径。
2. 迁移：Alembic 唯一 DDL 入口，禁止运行时自动建表。
3. 数据校验：`pydantic`（运行态）+ `jsonschema`（workpackage 契约）双层校验。
4. 缓存：Redis 仅用于查询加速与队列辅助，不作为真相源。

### Authentication & Security

1. 鉴权模型：沿用现有 `viewer/oncall/admin` 角色边界，不因 nanobot 迁移改变。
2. 审计要求：确认动作、发布动作、阻断动作必须具备 actor/reason/trace_id。
3. 数据安全：LLM 交互默认脱敏展示；敏感字段不得进入公开观测视图。

### API & Communication Patterns

1. API 风格：保持 REST 合约稳定，不引入 GraphQL。
2. 错误语义：保持现有阻断语义（如 INVALID_PAYLOAD、blocked/error），禁止伪成功。
3. 服务通信：`factory_agent -> governance_api/runtime` 维持现有协议与事件模型。

### Frontend Architecture

1. 运行态可观测前端继续采用现有页面体系，重点保证 `data-testid` 稳定与语义可读。
2. 前端不承担核心指标计算，指标以后端聚合结果为准。
3. 门禁状态与阻断原因必须可视化，不允许仅展示成功路径。

### Infrastructure & Deployment

1. 发布策略：单轨切换到 nanobot；No-Go 仅延期，不回退。
2. CI 门禁：新增 nanobot 迁移专项门禁（真实链路、事件一致性、回执一致性）。
3. 环境策略：切换窗口冻结底座依赖升级，避免复合变更。

### Decision Impact Analysis

**Implementation Sequence:**
1. 实现 nanobot 适配层（不改外部契约）。
2. 接入 dryrun/publish 编排并保持事件语义一致。
3. 完成四类强门禁测试并在 CI 固化。
4. 执行单轨切换并进入高强度观测窗口。
5. 切换稳定后再规划底座依赖升级。

**Cross-Component Dependencies:**
1. 编排决策直接影响 observability 事件链路与 runtime 回执追溯。
2. workpackage_schema/skills 决策影响打包、发布、验收全流程。
3. 安全与审计决策影响 API、前端展示与合规验收口径。


## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
12 个高风险冲突点（命名、结构、格式、事件、门禁、审计、测试口径）。

### Naming Patterns

**Database Naming Conventions:**
- schema/table/column 全部 `snake_case`。
- 主键统一 `id`，外键统一 `<entity>_id`。
- 审计字段统一：`created_at/updated_at/created_by/updated_by`。

**API Naming Conventions:**
- 路径资源名使用 `kebab-case`，参数名使用 `snake_case`。
- `workpackage_id` 与 `version` 必须成对出现，禁止单独传递。
- 观测接口字段语义固定：`source/event_type/status/pipeline_stage`。

**Code Naming Conventions:**
- Python 文件/函数/变量统一 `snake_case`。
- 领域对象与 DTO 使用语义前缀：`Workpackage*`, `Runtime*`, `Observability*`。
- Adapter 命名固定：`nanobot_adapter.py`，禁止出现并行第二实现命名。

### Structure Patterns

**Project Organization:**
- nanobot 接入仅允许在 `packages/factory_agent/` 内扩展。
- 外部契约层（CLI/API）不得直接依赖 nanobot SDK。
- 门禁逻辑归并于 workflow/service，禁止散落在 router/cli。

**File Structure Patterns:**
- `workpackage_schema` 为唯一协议入口，版本通过 `registry.json` 路由。
- `workpackages/bundles/<bundle>/workpackage.json + skills/` 为最小可执行包结构。
- 缺 `workpackage.json` 的 bundle 视为非法目录。

### Format Patterns

**API Response Formats:**
- 成功响应：`{status, data, meta}`（按现有契约兼容映射）。
- 失败响应：`{status: "error|blocked", code, message, details}`。
- 阻断场景必须返回可审计 `reason`，禁止仅返回布尔失败。

**Data Exchange Formats:**
- JSON 字段统一 `snake_case`。
- 时间统一 ISO-8601（UTC 带时区）。
- `runtime_receipt_id` 在执行、事件、审计三个视图中同值可追踪。

### Communication Patterns

**Event System Patterns:**
- 命名：`<stage>_<action>`（如 `runtime_submit_requested`）。
- 事件最小字段：`trace_id, source, event_type, status, occurred_at, payload_summary`。
- 发布链路事件序列固定：`created -> llm_confirmed -> packaged -> dryrun_finished -> publish_confirmed -> submitted -> accepted -> running -> finished`。

**State Management Patterns:**
- 状态推进只允许在 orchestrator/workflow 层执行。
- 禁止跨层直接改状态（router/repository 不得推进业务状态）。
- 状态非法跳转必须抛阻断错误并记审计。

### Process Patterns

**Error Handling Patterns:**
- 关键依赖失败统一 `blocked/error`，绝不 fallback。
- LLM/Runtime 失败必须保留原始错误摘要（脱敏后）。
- No-Go 处理方式是“延期”，不是技术回退。

**Loading State Patterns:**
- UI 加载状态与后端状态机一致（不可出现 UI 成功而后端阻断）。
- 阶段性按钮可用性由门禁状态驱动（confirm gate）。

### Enforcement Guidelines

**All AI Agents MUST:**
- 仅通过 `workpackage_schema/registry.json` 解析协议版本；
- 仅通过 `factory_agent` 适配层调用 nanobot；
- 在无回退策略下满足四类强门禁测试后才允许切换。

**Pattern Enforcement:**
- CI 增加 `check_workpackage_cleanup.sh` + nanobot 迁移专项门禁；
- 代码评审新增“边界矩阵”检查项；
- 违反规则必须附架构例外说明并经人工确认。

### Pattern Examples

**Good Examples:**
- `packages/factory_agent/nanobot_adapter.py` 提供单一编排入口；
- `workpackage_schema/examples/v1/...` 与 schema 同版本校验通过；
- 事件链路中 `runtime_receipt_id` 全链路一致。

**Anti-Patterns:**
- router 直接调用 nanobot SDK；
- 缺失 `confirm_publish` 仍允许 `submitted`；
- `workpackage_id` 无 `version` 仍执行；
- 失败时返回“success + warning”。


## Project Structure & Boundaries

### Complete Project Directory Structure

```text
spatial-intelligence-data-factory/
├── workpackage_schema/
│   ├── registry.json
│   ├── schemas/
│   │   └── v1/workpackage_schema.v1.schema.json
│   ├── templates/
│   │   └── v1/
│   └── examples/
│       └── v1/
├── workpackages/
│   ├── bundles/
│   │   └── <bundle_id>/
│   │       ├── workpackage.json
│   │       ├── skills/
│   │       ├── scripts/
│   │       ├── observability/
│   │       └── config/
│   └── README.md
├── packages/
│   ├── factory_agent/
│   │   ├── agent.py
│   │   ├── nanobot_adapter.py
│   │   ├── llm_gateway.py
│   │   ├── dryrun_workflow.py
│   │   ├── publish_workflow.py
│   │   └── routing.py
│   ├── factory_cli/
│   ├── governance_runtime/
│   ├── address_core/
│   └── trust_hub/
├── services/
│   ├── governance_api/
│   │   ├── app/routers/
│   │   ├── app/services/
│   │   └── app/repositories/
│   ├── governance_worker/
│   └── trust_data_hub/
├── scripts/
│   ├── check_workpackage_cleanup.sh
│   ├── run_p0_workpackage.py
│   └── run_line_feedback_ci_block_demo.py
├── tests/
│   ├── test_factory_agent_*.py
│   ├── test_workpackage_*.py
│   └── web_e2e/
├── docs/
│   ├── architecture/
│   ├── stories/
│   └── acceptance/
├── output/
│   ├── workpackages/
│   └── dashboard/
└── .github/workflows/
```

### Architectural Boundaries

**API Boundaries:**
1. `factory_cli` 只调用 `factory_agent`，不直接触达 DB。
2. `governance_api` 负责 HTTP 合约与错误语义，不承载编排内核。
3. `factory_agent` 通过 `governance_api/runtime` 完成发布与回执闭环。

**Component Boundaries:**
1. nanobot 仅通过 `packages/factory_agent/nanobot_adapter.py` 接入。
2. `agent.py` 负责编排流程控制，不直接耦合 SDK 细节。
3. `address_core/trust_hub` 作为领域能力层，不承担流程控制状态机。

**Service Boundaries:**
1. Router -> Service -> Repository 分层强制。
2. 状态推进只在 workflow/service 层执行。
3. Repository 只做持久化，不做业务编排。

**Data Boundaries:**
1. PostgreSQL 为真相源；Redis 仅缓存/队列辅助。
2. `workpackage_schema` 为工作包协议唯一入口。
3. `workpackage.json + skills/` 为 bundle 最小可执行单元。

### Requirements to Structure Mapping

**Feature/Epic Mapping:**
1. 工厂需求确认与编排：`packages/factory_agent/*`
2. 运行态观测与追溯：`services/governance_api/app/routers/observability.py` + `output/dashboard/*`
3. 工作包协议治理：`workpackage_schema/*`
4. 发布与运行闭环：`packages/governance_runtime/*` + `services/governance_worker/*`

**Cross-Cutting Concerns:**
1. 审计与门禁：`services/governance_api/app/services/*` + `tests/*gate*`
2. 契约一致性：`tests/test_workpackage_*`
3. No-Fallback 约束：`tests/test_factory_agent_*` + E2E 测试集

### Integration Points

**Internal Communication:**
1. `factory_cli -> factory_agent -> governance_api/runtime`
2. `governance_api -> governance_worker -> runtime_store`
3. `factory_agent -> llm_gateway -> 真实LLM`

**External Integrations:**
1. 真实 LLM provider
2. 可信数据 API（via trust_hub）
3. PostgreSQL / Redis 基础设施

**Data Flow:**
1. 用户请求 -> 需求确认 -> 工作包生成 -> dryrun -> 发布确认 -> runtime 提交
2. runtime 执行 -> 事件落库 -> 观测 API -> dashboard 展示
3. 失败阻断 -> 审计留痕 -> 人工确认闭环

### File Organization Patterns

**Configuration Files:**
- 运行配置集中在 `config/`，环境变量通过 `.env` 体系管理。

**Source Organization:**
- 业务编排在 `packages/factory_agent/`，服务接口在 `services/governance_api/`。

**Test Organization:**
- 核心编排测试：`tests/test_factory_agent_*`
- 协议与清理守卫：`tests/test_workpackage_*`
- UI E2E：`tests/web_e2e/*`

**Asset Organization:**
- 运行证据：`output/workpackages/*`
- 看板数据：`output/dashboard/*`
- 文档产物：`docs/*` 与 `_bmad-output/*`


## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
1. nanobot 单轨迁移与“外部契约不变”策略一致，无显性冲突。
2. `workpackage_schema` 一级入口、`skills` 强约束、bundle 结构要求已与发布链路一致。
3. No-Fallback、真实 LLM、PG-only、审计留痕与门禁策略在各章节表述一致。

**Pattern Consistency:**
1. 命名/结构/格式/事件/流程模式与核心决策匹配。
2. `factory_agent -> nanobot_adapter` 的单入口规则与边界矩阵一致。
3. API 错误语义与 UI 阻断可视化要求一致。

**Structure Alignment:**
1. 目录结构支持当前架构决策与迁移路径。
2. 组件边界清晰：CLI/API/Agent/Runtime/Schema 各自职责明确。
3. 集成点（LLM、Runtime、Observability）均有明确落点。

### Requirements Coverage Validation ✅

**Feature/Epic Coverage:**
1. 工厂确认-打包-发布链路有完整架构支撑。
2. 运行态观测（事件、回执、下钻）有完整结构与字段约束。
3. 工作包协议治理与 bundles 清理规则已覆盖。

**Functional Requirements Coverage:**
1. `workpackage_id@version` 执行与追溯要求已覆盖。
2. 人机确认门禁与阻断闭环要求已覆盖。
3. dry-run 报告结构与图谱要求已覆盖。

**Non-Functional Requirements Coverage:**
1. No-Fallback/No-Mock：已作为强门禁。
2. 审计合规：动作与事件最小字段已定义。
3. 可观测性：事件语义与中文可读要求已对齐。
4. 兼容性：迁移窗口版本冻结策略已定义。

### Implementation Readiness Validation ✅

**Decision Completeness:**
- 关键决策已具备“策略 + 边界 + 门禁 + 版本”四要素。

**Structure Completeness:**
- 项目结构与边界定义可直接指导 story 拆解与实现。

**Pattern Completeness:**
- 已覆盖多 agent 协作最易冲突的核心点（命名、事件、状态、错误）。

### Gap Analysis Results

**Critical Gaps:** 无阻断级缺口。  
**Important Gaps:**
1. `nanobot_adapter.py` 的接口契约还需形成单独 ADR（输入输出模型与异常字典）。
2. 迁移专项 CI 门禁脚本尚未在本文档中细化到命令级。
3. 事件字段字典（`event_type` 枚举）建议补一页规范附录。

**Nice-to-Have Gaps:**
1. 依赖升级路线图（迁移后阶段）。
2. 性能压测口径（端到端时延分位）落地细则。

### Validation Issues Addressed

1. 已明确“无回退”策略为 No-Go 延期，不做技术回滚。
2. 已将测试约束上升为架构约束（真实链路、事件一致、回执一致）。
3. 已固定 `workpackage_schema` 一级目录与 `skills` 组成关系。

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] 项目上下文与约束已分析
- [x] 复杂度与边界已明确
- [x] 技术约束与迁移策略已定义
- [x] 跨切关注点已识别

**✅ Architectural Decisions**
- [x] 核心决策已形成
- [x] 技术基线与版本策略已明确
- [x] 集成与门禁模式已定义
- [x] 风险控制策略已落地

**✅ Implementation Patterns**
- [x] 命名/结构/通信/流程规则已定义
- [x] 冲突点防护已覆盖
- [x] 反模式已列出
- [x] 强制规则已给出

**✅ Project Structure**
- [x] 目录结构完整
- [x] 组件边界清晰
- [x] 需求到结构映射完成
- [x] 集成点与数据流明确

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION  
**Confidence Level:** High

**Key Strengths:**
1. 决策-模式-结构三层闭环完整。
2. 对无回退迁移场景给出了可执行门禁。
3. 与现有仓库边界和契约治理体系高度一致。

**Areas for Future Enhancement:**
1. `nanobot_adapter` ADR 细化。
2. 迁移专项 CI 细则文档化。
3. 事件字典与错误码字典标准化补充。

### Implementation Handoff

**AI Agent Guidelines:**
1. 严格按边界矩阵执行，不得跨层侵入。
2. 严格按模式规则实现，禁止 fallback 成功语义。
3. 所有迁移提交必须附门禁测试证据。

**First Implementation Priority:**
实现 `packages/factory_agent/nanobot_adapter.py` 与最小端到端接线（不改外部契约）。
