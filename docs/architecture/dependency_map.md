# 依赖关系图（Dependency Map）

## 1. 依赖分层原则

1. 单向依赖：上层依赖下层，不允许反向调用。
2. 稳定依赖：高变模块依赖低变抽象，不直接依赖具体实现。
3. 数据访问收敛：仅 Repository/DAO 访问数据库。

## 2. 模块依赖关系（文本图）

```text
Factory CLI
  -> Factory Agent
  -> Governance API

Factory Agent
  -> LLM Gateway
  -> Publish Workflow
  -> Dryrun Workflow
  -> Runtime Adapter

Governance API
  -> Application Service
  -> Repository
  -> Observability Service

Runtime Orchestrator / Worker
  -> Address Governance Core
  -> Trust Hub Query Interface
  -> Repository
  -> Queue Adapter (Redis/RQ)

Address Governance Core
  -> Domain Models
  -> Trust Hub Query Interface (abstract)
  -> Repository Interface (abstract)

Trust Hub
  -> External Tools/APIs
  -> Repository

Observability Service
  -> Repository (audit + runtime + governance)
  -> Dashboard View Model
```

## 3. 数据依赖关系（PG 多 schema）

1. `governance`
- 被 `Governance API`、`Runtime Worker` 读写。
- 保存任务、结果、审核闭环。

2. `runtime`
- 被 `Factory Agent publish workflow`、`Runtime Worker` 读写。
- 保存工作包发布、版本、执行记录。

3. `trust_meta`
- 被 `Trust Hub` 主写，`Core/API` 只读。
- 保存来源、快照、质量报告、active release。

4. `trust_data`
- 被 `Trust Hub` 主写，`Core` 查询消费。
- 保存可检索可信数据。

5. `audit`
- 被所有关键流程写入审计事件。
- 被 Observability 查询、回放、告警模块消费。

## 4. API 边界与依赖约束矩阵

| 调用方 | 可依赖 | 禁止依赖 |
|---|---|---|
| CLI | Agent/API SDK | DB/Repository/ORM |
| Agent | LLM Gateway、Workflow、Runtime Adapter | FastAPI Handler、SQL 细节 |
| API Router | Application Service | CLI、Worker 内部实现 |
| Application Service | Core、Repository、Observability Service | HTTP Response 对象拼装逻辑 |
| Core | 抽象接口（Trust/Repo） | Web Framework、Queue SDK |
| Trust Hub | External Provider Adapter、Repository | CLI、前端页面 |
| Observability | Repository、聚合器 | 直接修改业务状态机 |

## 5. 不允许的耦合方式（依赖视角）

1. 反向依赖
- `Core -> API Router`
- `Repository -> Service/Router`

2. 横向穿透
- `CLI -> DB`
- `Frontend -> DB`
- `Agent -> ORM Model 直写`

3. 循环依赖
- `Trust Hub <-> Address Core` 双向直接调用。
- `Observability <-> Runtime Worker` 双向业务控制。

4. 隐式运行时耦合
- 通过环境变量暗开 fallback 规避失败。
- 通过本地文件替代数据库真相源且未声明模式。

## 6. 守护与检查清单

1. 架构检查
- 新增模块必须声明“上游依赖/下游依赖/禁止依赖”。

2. 测试检查
- 增加依赖边界测试（禁止 CLI 直接 DB、禁止 Core 引用 FastAPI）。

3. 发布检查
- DDL 变更仅允许 Alembic；
- 发现非 Alembic 生产 DDL 路径时阻断发布。

4. 评审检查
- PR 模板中增加“是否引入新耦合”与“是否违反 No-Fallback”必填项。
