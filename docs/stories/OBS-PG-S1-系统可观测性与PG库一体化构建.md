# OBS-PG-S1 - 系统可观测性与 PG 库一体化构建

## Story 目标

把“系统可观测性能力”与“PG 库持久化能力”合并为一个可交付 Story，打通采集、聚合、存储、查询、告警、回放全链路。

本 Story 架构主规范（强制）：

1. `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`
2. `docs/architecture/system_overview.md`
3. `docs/architecture/module_boundaries.md`
4. `docs/architecture/dependency_map.md`

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

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC C（质量门禁与可观测交付）+ EPIC D（工程治理与可维护性）。
2. 架构对齐：
- `docs/architecture/system_overview.md`
- `docs/architecture/module_boundaries.md`
- `docs/architecture/dependency_map.md`

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

## 子任务拆解（执行序列）

1. OBS-PG-S1-T1：能力面板字段契约化（API + 页面 + 测试）
- 目标：把 `observability-dashboard-enhancement` 中能力面板字段完整映射到 `lab/observability`。
- AC：
  - `snapshot/events/timeseries` 返回字段包含能力面板所需最小集合（状态、延迟、错误率、吞吐、告警计数）。
  - 页面按统一字段渲染，不再依赖临时拼装字段。
  - 新增契约测试：字段缺失时返回 `blocked/error`，不允许 fallback。
  - MVP 量化阈值：`snapshot` 接口 P95 响应时间 <= 2s（1000 条事件样本）。

2. OBS-PG-S1-T2：Trace 回放与告警 Ack 闭环强化
- 目标：保证 `trace replay/alert ack` 可追踪、可审计、可复查。
- AC：
  - 回放接口按 `trace_id/task_id/workpackage_id` 返回完整链路。
  - 告警 ack 写入审计字段（原因、确认人、时间、结论）。
  - 新增 API 集成测试覆盖成功与阻塞分支。
  - MVP 量化阈值：回放链路完整率 >= 99%（以测试样本集统计）。

3. OBS-PG-S1-T3：PG 多 schema 查询口径收敛
- 目标：把观测查询口径统一到 `governance/runtime/trust_meta/trust_data/audit`。
- AC：
  - 关键查询 SQL 与仓储接口不再出现旧命名分叉。
  - Alembic 迁移作为唯一生产 DDL 入口。
  - 增加数据库契约测试，校验 schema/table/index 最小基线。

4. OBS-PG-S1-T4：一键验收证据固化
- 目标：输出可审阅的 JSON/Markdown 证据并纳入评审。
- AC：
  - 验收脚本包含 OBS-PG-S1 子任务结果分段。
  - 输出路径固定并在 PRD/架构评审报告中可追溯引用。
  - 任一子任务失败时整体验收失败，不静默降级。

## 模块边界与 API 边界（回归对齐）

1. 所属模块：`observability service`、`governance_api.lab`、`repository`、`audit`。
2. 上游入口：API 查询、Worker/Agent 事件写入。
3. 下游依赖：`governance/runtime/audit` 数据汇聚与查询聚合器。
4. API 边界：观测接口仅查询与告警确认，不反向驱动业务状态机。

## 依赖与禁止耦合（回归对齐）

1. 允许依赖：`api -> observability service -> repository`。
2. 禁止耦合：
- observability 直接修改任务状态。
- 页面绕过 API 直连数据库。
