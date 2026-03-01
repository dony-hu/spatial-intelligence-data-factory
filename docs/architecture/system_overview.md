# 系统架构总览（基于 PRD）

## 1. 架构目标与约束

本架构以 `docs/prd-spatial-intelligence-data-factory-2026-02-27.md` 为基线，面向以下目标：

1. 地址治理主链路稳定、可解释、可复核。
2. 工厂 CLI 与工厂 Agent 协作闭环可追踪，并支持 LLM 需求确认与治理流程试运行。
3. 工作包发布到 Runtime 后具备可审计、可观测、可回放的执行闭环。
4. Trust Hub 积累可信外部能力与可信互联网数据，作为治理能力增强层。
5. 严格 No-Fallback：关键链路异常必须显式 `blocked/error`，禁止静默降级。

强制架构基线：

1. `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`

## 2. 模块划分（L0-L4）

1. L0 交互入口层
- Factory CLI
- Governance API（含 Lab 可观测接口）

2. L1 编排与控制层
- Factory Agent（意图路由、LLM 网关、dryrun/publish 编排）
- Runtime Orchestrator（任务调度、状态机、工作包执行）

3. L2 领域能力层
- Address Governance Core（标准化/解析/召回/评分/复核）
- Trust Hub（能力目录、可信数据查询、来源管理）

4. L3 数据与审计层
- PostgreSQL 多 schema：`governance/runtime/trust_meta/trust_data/audit`
- Redis/RQ（异步队列）

5. L4 可观测与门禁层
- Observability API + 页面
- 验收与测试门禁（unit/integration/real-llm-gate/full）
- 证据产物（JSON/Markdown）

## 3. 模块职责（摘要）

1. Factory CLI
- 提供统一命令入口（需求确认、dryrun、publish、查询）。
- 只做交互与参数编排，不承载业务决策。

2. Factory Agent
- 对话意图识别与路由。
- 调用 LLM 网关完成需求确认。
- 驱动 dryrun/publish 工作流，回传结构化结果与审计事件。

3. Governance API
- 对外提供任务、查询、观测、告警 ACK、回放接口。
- 统一错误语义与契约校验。

4. Runtime Orchestrator / Worker
- 执行任务状态机与工作包入口。
- 产出执行证据并写入审计与观测事件。

5. Address Governance Core
- 纯领域逻辑模块，输出标准结果契约（含 `strategy/confidence/evidence`）。
- 不依赖 CLI/API/页面实现细节。

6. Trust Hub
- 管理可信来源、能力元数据与快照。
- 提供可复用查询能力给治理主链路与评估流程。

7. Data Layer（PG + Redis）
- PG 承载事务、运行态、可信数据和审计。
- Redis/RQ 承载异步执行，不保存业务真相数据。

8. Observability Layer
- 汇聚事件、指标、告警并对外查询。
- 支持 `trace_id/task_id/workpackage_id` 关联回放。

## 4. 端到端数据流

1. 需求确认流
- CLI -> Agent -> LLM Gateway -> Agent -> `governance`（需求记录）-> CLI

2. 治理试运行流（Dryrun）
- CLI -> Agent(dryrun workflow) -> Runtime Entrypoint -> Governance Core -> `governance/audit` -> 观测事件回写 -> CLI/API 查询

3. 发布执行流（Publish）
- CLI/API -> Agent(publish workflow) -> Runtime 发布 -> 执行触发 -> `runtime/governance/audit` 落库 -> Observability 聚合 -> Dashboard 展示

4. Trust 增强流
- 外部工具/API -> Trust Hub -> `trust_meta/trust_data` -> Governance Core 查询 -> 结果证据回写

## 5. API 边界（高层）

1. 外部边界（Northbound）
- CLI 命令接口
- HTTP API：`/v1/governance/*`

2. 内部边界（East-West）
- Agent <-> Runtime（工作包契约）
- Governance API <-> Repository（仓储接口）
- Runtime/Worker <-> Core（领域服务接口）
- Core <-> Trust Hub（只读查询接口）

3. 数据边界（Southbound）
- 只允许 Repository/DAO 访问 PG。
- 只允许 Queue Adapter 访问 Redis/RQ。

## 6. 依赖关系（概览）

1. CLI 依赖 Agent/API，不依赖 DB。
2. Agent 依赖 LLM Gateway、Workflow 组件、Runtime Adapter，不依赖页面或 SQL。
3. API/Worker 依赖 Core 与 Repository，不依赖 CLI 实现。
4. Core 依赖抽象仓储与 Trust 查询接口，不依赖 FastAPI/RQ。
5. Observability 依赖审计事件与运行记录，不反向驱动业务状态机。

## 7. 不允许的耦合方式（总则）

1. CLI 直接读写数据库。
2. 页面层直接访问数据库或 Runtime 内部表。
3. Core 直接调用 HTTP Framework 或 Web Response 对象。
4. 模块通过共享可变全局状态传递业务上下文。
5. 关键链路使用 fallback 掩盖真实失败（必须显式 `blocked/error`）。
6. 绕过 Alembic 新增生产 DDL 路径。
