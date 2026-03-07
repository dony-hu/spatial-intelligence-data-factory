# Architecture - 空间智能数据工厂（Level 4）

> 文档状态：历史参考
> 降级日期：2026-03-06
> 当前用途：保留早期总架构叙事与阶段背景，不再作为新 Story/评审/实现的默认依据。
> 当前有效入口：`docs/architecture/架构索引.md`

## 1. 文档信息

- 文档版本：v1.0
- 创建日期：2026-02-27
- 上游输入：`archive/docs/formal/product/prd-2026-02-27.md`
- 适用范围：平台层架构（不含地区本地化实现细节）
- 文档语言：中文（遵循仓库 AGENTS 规则）

## 2. 架构目标

本架构用于支撑 PRD 的四类核心目标：

1. 地址治理主链路稳定、可解释、可复核。
2. 治理控制面可编排、可审计、可观测。
3. 质量门禁与发布门禁形成 Go/No-Go 闭环。
4. 工程结构可持续演进，降低维护复杂度。

## 3. 现状架构（As-Is）

### 3.1 模块分层

1. 服务层（`services/`）
- `governance_api`：FastAPI 提供任务、评审、规则、运维、Lab 接口。
- `governance_worker`：任务执行与落库编排。
- `trust_data_hub`：可信数据查询与管理 API。

2. 领域能力层（`packages/`）
- `address_core`：地址治理流水线（normalize/parse/match/score）。
- `agent_runtime`：运行时适配与策略选择。
- `factory_agent`、`factory_cli`：工厂 Agent 与 CLI 交互。

3. 编排与工具层（`tools/`, `scripts/`）
- Agent Server、流程编译器、process tools、各类运行脚本与门禁脚本。

4. 交付与验证层
- `tests/`、`services/*/tests/`：单测/集成/E2E。
- `.github/workflows/`：smoke、P0、nightly 门禁。
- `output/`：门禁产物、看板数据与证据报告。

### 3.2 现状优势

1. 关键服务边界已形成，API/Worker/Hub 职责可识别。
2. 质量门禁体系已有基础（P0 + Nightly + SQL + Web E2E）。
3. 地址治理主链路与测试资产具备可运行雏形。

### 3.3 现状问题

1. 多入口并存（FastAPI/Flask/HTTPServer/脚本）导致运行模型分散。
2. `tools/` 与 `scripts/` 承担大量业务逻辑，边界偏松。
3. 大文件与多模式 fallback 增加长期维护和排障成本。
4. 环境可移植性存在风险（历史环境产物/本机绑定痕迹）。

## 4. 目标架构（To-Be）

### 4.1 分层与边界

1. L0 治理与门禁层
- 统一质量门禁策略、发布门禁策略、审计证据规范。

2. L1 控制平面层
- 统一任务编排入口、运行时策略路由、确认/审批编排。

3. L2 领域服务层
- `governance_api`、`governance_worker`、`trust_data_hub` 作为标准服务面。

4. L3 领域能力层
- `address_core`、`agent_runtime` 作为稳定能力库。

5. L4 交付与可观测层
- 看板、报告、工作包产物、测试证据统一归档与消费。

### 4.2 核心设计原则

1. 服务边界清晰：API 负责协议与编排入口，领域能力负责纯逻辑。
2. 失败语义明确：禁止“无产物成功”，所有失败路径可追踪。
3. 配置优先：运行模式由配置控制，默认安全、可审计、阻塞可确认。
4. 证据优先：每个关键流程必须有 machine-readable 证据产物。
5. 渐进式重构：优先稳定主链路，再收敛入口和目录结构。

## 5. 关键运行链路设计

### 5.1 治理任务主链路

`Client -> Governance API -> Queue/Worker -> Address Core + Runtime -> Repository -> API Query`

关键控制点：

1. 任务状态机：`PENDING -> RUNNING -> SUCCEEDED/FAILED/BLOCKED`。
2. 结果契约：`strategy/confidence/evidence` 必填。
3. 审核闭环：低置信度结果可进入人工决策并回写。

### 5.2 质量门禁链路

`PR/Push -> CI Workflow -> Test Suites -> Gate Decision -> Evidence Artifacts`

关键控制点：

1. P0 门禁阻断核心回归。
2. 夜间门禁执行重试与失败分类。
3. 看板与门禁产物数据一致。

## 6. 数据与存储架构

1. 事务与状态数据：PostgreSQL（支持 SQLite 本地最小验证模式）。
2. 异步任务队列：Redis + RQ（支持 sync/in_memory 研发模式）。
3. 交付证据：`output/` 统一产物目录（JSON/JSONL/Markdown）。
4. 配置与契约：`config/`、`contracts/`、`schemas/` 统一管理。

## 7. 横切关注点

1. 可观测性
- 关键任务状态、失败原因、门禁结果、执行耗时必须可查询。

2. 安全与合规
- 不提交明文密钥，执行最小权限，保留关键审计轨迹。

3. 可靠性
- 异常路径阻塞并进入人工确认，失败可重放，门禁可重复执行。

## 8. 架构决策（ADR 摘要）

1. ADR-001：以服务化（FastAPI）作为主对外接口形态。
2. ADR-002：地址治理逻辑沉淀在 `packages/address_core`，避免散落脚本化实现。
3. ADR-003：门禁结果必须输出结构化证据，作为发布决策依据。
4. ADR-004：保留本地最小运行模式，但必须通过显式开关控制。

## 9. 迁移与实施计划（面向 Implementation）

### 9.1 Stage 1（稳定主链路）

1. 固化治理任务主链路契约与关键测试。
2. 固化门禁产物格式与看板消费接口。

### 9.2 Stage 2（边界收敛）

1. 收敛多入口运行模式，明确标准启动路径。
2. 将高耦合脚本逻辑逐步迁移到可测试模块。

### 9.3 Stage 3（工程治理）

1. 梳理环境与依赖管理方式，提升跨机器可复现性。
2. 拆分超大模块并补齐回归测试。

## 10. 风险与缓解

1. 风险：重构影响既有链路稳定性。
- 缓解：先补回归测试，再做分阶段迁移。

2. 风险：多运行模式带来行为不一致。
- 缓解：引入默认模式与显式开关策略，输出运行态标识。

3. 风险：产物增长导致仓库治理压力。
- 缓解：制定产物归档策略与保留策略，避免无界增长。

## 11. 验收标准（Architecture 完成定义）

1. 架构文档与 PRD 范围一致，边界明确。
2. 关键运行链路与门禁链路具备可执行描述。
3. 提供可落地迁移计划与阶段验收标准。
4. 可作为 `sprint-planning/create-story` 的直接输入。
