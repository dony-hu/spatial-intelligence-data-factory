# 模块边界定义（Module Boundaries）

## 1. 目标

定义系统模块边界、职责归属与 API 边界，防止职责漂移与隐式耦合。

## 2. 模块划分与职责

### 2.1 交互入口域

1. `factory_cli`
- 职责：用户命令入口、参数校验、结果展示。
- 输入：用户命令、配置参数。
- 输出：标准化请求给 Agent/API；结构化结果给用户。

2. `governance_api`（含 `lab/observability`）
- 职责：对外 HTTP 契约、认证鉴权、请求编排、错误语义标准化。
- 输入：外部 HTTP 请求。
- 输出：任务状态、治理结果、观测快照、事件、告警处理结果。

### 2.2 编排控制域

1. `factory_agent`
- 职责：意图识别、需求确认对话、dryrun/publish 工作流编排。
- 输入：CLI/API 发起的任务请求、LLM 配置、工作包元数据。
- 输出：结构化执行结果、审计事件、阻塞原因。

2. `runtime_orchestrator` / worker
- 职责：任务调度、状态机推进、工作包执行与结果回传。
- 输入：发布/执行请求、运行模式配置（sync/rq）。
- 输出：运行结果、审计事件、观测指标。

### 2.3 领域能力域

1. `address_core`
- 职责：地址治理领域逻辑（normalize/parse/match/score/review）。
- 输入：原始地址、规则集、可信数据查询结果。
- 输出：治理结果对象（必须含 `strategy/confidence/evidence`）。

2. `trust_hub`
- 职责：可信来源注册、能力目录、快照查询与验证能力聚合。
- 输入：来源配置、外部工具/API 回包。
- 输出：可信数据查询结果、来源质量与审计信息。

### 2.4 数据与基础设施域

1. Repository/DAO
- 职责：持久化访问抽象、事务边界、SQL 收敛。
- 输入：领域对象、查询条件。
- 输出：领域可消费数据模型。

2. Queue Adapter（Redis/RQ）
- 职责：消息入队、消费、重试控制。
- 输入：执行任务 payload。
- 输出：任务执行触发结果与状态通知。

3. Migration（Alembic）
- 职责：唯一 DDL 变更路径。
- 输入：schema 演进定义。
- 输出：可回放迁移记录。

## 3. API 边界

### 3.1 对外 API（Northbound）

1. Governance API
- 任务类：提交任务、查询任务、流程状态。
- 观测类：`snapshot/events/timeseries/stream/view/trace replay/alert ack`。
- 规则与审核类：规则管理、人工审核回写。

2. CLI 命令边界
- 仅调用 Agent/API，不直连 DB。
- 命令仅代表用例入口，不包含业务规则实现。

### 3.2 对内 API（East-West）

1. Agent <-> LLM Gateway
- 仅交换需求确认请求/响应，不共享底层 SDK 对象。

2. Agent <-> Runtime
- 通过工作包契约（workpackage id/version/entrypoint/env）交互。

3. API/Worker <-> Core
- 通过领域服务接口交互，不透传 HTTP/ORM 细节。

4. Core <-> Trust Hub
- 通过查询接口取可信数据，不直接访问 trust_data 物理表。

5. Service <-> Repository
- 通过仓储抽象，禁止直接拼接跨 schema SQL。

## 4. 数据流（边界视角）

1. 请求进入 API 或 CLI。
2. 编排层决定流程与运行模式。
3. 领域层执行治理逻辑并生成结果。
4. Repository 统一持久化到 `governance/runtime/trust_meta/trust_data/audit`。
5. Observability 读取事件与指标输出给页面与告警接口。

## 5. 不允许的耦合方式（强制）

1. `factory_cli` -> PostgreSQL 直连。
2. `address_core` -> FastAPI request/response 直接依赖。
3. `governance_api` -> 直接依赖 `factory_cli` 内部实现。
4. 页面前端 -> 数据库直连或读取内部文件作为唯一数据源。
5. `trust_hub` 与 `address_core` 双向直接调用形成循环依赖。
6. worker 直接写页面缓存替代标准观测落库。
7. 运行时通过 `if fallback` 隐式吞错并返回成功。
8. 新增非 Alembic 生产 DDL 脚本并进入发布链路。

## 6. 边界守护策略

1. 测试守护
- 边界契约测试：API 字段、错误语义、回放一致性、告警 ACK 审计。
- No-Fallback 测试：关键路径失败必须 `blocked/error`。

2. 工程守护
- 代码评审检查禁止耦合清单。
- CI 增加仓库卫生与 DDL 路径检查。

3. 文档守护
- 新 Story 必须声明所属模块与依赖边界。
- spec 融合状态与 workflow status 同步更新。
