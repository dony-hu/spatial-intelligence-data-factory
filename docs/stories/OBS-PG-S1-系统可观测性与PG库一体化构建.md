# OBS-PG-S1 - 系统可观测性与 PG 库一体化构建

## Story 目标

把“系统可观测性能力”与“PG 库持久化能力”合并为一个可交付 Story，打通采集、聚合、存储、查询、告警、回放全链路。

本 Story 架构主规范（强制）：

1. `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`

## 验收标准（AC）

1. 新增统一观测数据模型并完成 PG 落库（事件/指标/告警）。
2. 提供统一查询 API：`snapshot/events/timeseries/trace replay/alert ack`。
3. 关键链路（CLI/Agent/API/Worker/Core/Trust）产生可关联 `trace_id` 事件。
4. 不允许 fallback，异常必须返回 `blocked/error` 并写审计。
5. 管理看板可读取新模型最小字段并展示告警与趋势。
6. 一键验收脚本输出 JSON/Markdown 并通过。
7. schema 命名完成收敛：`governance/runtime/trust_meta/trust_data/audit`。
8. DDL 入口收敛：Alembic 唯一入口（禁止新增并行生产 DDL 路径）。

## 技术范围

1. 数据库：
- 统一 PG schema 口径与索引策略。
- 提供必要 Alembic migration；初始化 SQL 仅保留测试/校验用途。

2. API：
- 在治理 API 内新增观测查询与告警处理接口。

3. Runtime 与 Worker：
- 增加观测埋点与事件持久化。

4. Dashboard：
- 升级 `lab/observability` 数据契约。

## 测试策略（强制 TDD）

1. 先补失败用例：
- 观测事件落库失败/阻塞语义
- API 查询契约
- trace 回放一致性
- 告警 ack 闭环

2. 再补实现，最后回归：
- 组件级测试
- API 集成测试
- E2E 验收脚本测试

## 交付物

1. 架构文档：
- `docs/architecture-observability-capability-2026-02-27.md`

2. Epic 文档：
- `docs/epic-observability-pg-unified-2026-02-27.md`

3. 代码与测试：
- 以 Story 开发阶段补齐（本阶段仅计划，不提前实现）。
