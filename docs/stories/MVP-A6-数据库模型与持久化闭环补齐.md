# Story: MVP-A6 数据库模型与持久化闭环补齐

## 目标

补齐地址治理 MVP 所需数据库能力，确保 CLI/Agent/LLM、工作包发布、治理主链路、Trust Hub 全部具备可追踪持久化。

## 验收标准

1. 治理任务查询链路以数据库为准，不依赖进程内内存态。
2. 工作包发布记录可入库并可按版本查询（含状态与证据引用）。
3. LLM 调用结果可区分 `success/error/blocked` 并可追踪，不允许 `fallback`。
4. Trust Hub 能力与数据沉淀可落库并与服务查询链路打通。
5. `trust_meta` 结构定义来源收敛，避免 SQL 与 migration 冲突。
6. 阻塞记录必须包含原因、人工确认人、确认结论与时间戳。

## 开发任务

1. 先补测试：读写一致性、发布记录、LLM 调用状态、Trust Hub 落库用例。
2. 再改实现：仓储层/发布层/schema 初始化路径对齐。
3. 最后验证：最小 MVP 全链路执行后可在 DB 查询到关键证据。

## 测试用例

1. 任务提交后服务重启，仍可查询任务与结果。
2. 发布工作包后可按 `workpackage_id + version` 查询发布记录。
3. LLM 调用失败场景记录为 `error/blocked`，且阻塞审批链路可检索。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC B（状态/结果落库）+ EPIC D（工程可维护性）。
2. 架构对齐：
- `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`
- `docs/architecture/dependency_map.md` 数据依赖关系。

## 模块边界与 API 边界

1. 所属模块：Repository/DAO、Alembic Migration、governance/runtime/trust_meta/trust_data/audit。
2. 上游入口：API/Agent/Worker 的持久化请求。
3. 下游依赖：PostgreSQL 多 schema 与迁移基线。
4. API 边界：业务服务只能经 Repository 访问数据库，不允许直连 SQL。

## 依赖与禁止耦合

1. 允许依赖：`service -> repository -> postgres`，`migration -> alembic`。
2. 禁止耦合：
- 新增并行生产 DDL 路径绕过 Alembic。
- 运行态内存数据作为任务查询唯一来源。
