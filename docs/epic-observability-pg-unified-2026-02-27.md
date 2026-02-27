# Epic - 系统可观测性与 PG 库一体化建设（2026-02-27）

## 1. Epic 目标

在当前地址治理主线基础上，完成“系统可观测性能力 + PG 库持久化能力”一体化建设，并形成可追踪、可查询、可告警、可回放的统一闭环。

核心要求：

1. 可观测事件/指标/告警统一模型。
2. 观测与治理关键数据统一落 PG（含多 schema 读写一致性）。
3. 保持 No-Fallback：关键观测链路异常必须显式 `blocked/error`。

主规范（强制）：

1. `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md` 作为 PG 与 schema 演进唯一架构基线。

## 2. In Scope

1. 统一可观测事件模型（trace/event/metric/alert）。
2. 统一 PG 表结构与索引（含 `address_line/control_plane/trust_meta/trust_db` 查询对齐）。
3. 统一查询 API（snapshot/events/timeseries/trace replay/alert ack）。
4. 管理看板最小升级（复用 `lab/observability`，接入新契约）。
5. 一键验收与证据产出（JSON/Markdown）。

补充强制范围：

1. schema 命名收敛到 `governance/runtime/trust_meta/trust_data/audit`。
2. Alembic 作为唯一 DDL 入口；初始化 SQL 仅保留只读校验/本地测试用途。

## 3. Out of Scope

1. 外部独立可观测平台（ELK/Tempo）作为强依赖。
2. 多租户 RBAC。
3. 历史全量回填。

## 4. 合并 Story（单 Story）

1. OBS-PG-S1：系统可观测性与 PG 库一体化构建
- 包含原“可观测性能力构建”与“PG 库建设”全部最小交付项。
- 采用 TDD：先失败测试 -> 再实现 -> 回归验收。
- 不允许 fallback，阻塞问题统一上报人工确认。

## 5. DoD（本 Epic）

1. 任一任务可按 `trace_id/task_id/workpackage_id` 回放链路。
2. 可查询观测快照、事件明细、指标趋势、告警状态。
3. 观测与治理关键记录均可在 PG 查到，且重启后可复查。
4. 阻塞/失败事件具备结构化审计字段（原因、确认人、结论、时间）。
5. 验收脚本输出 JSON + Markdown 证据并通过。
6. 代码库不再新增非 Alembic 的生产 DDL 路径，存在路径完成收敛计划并落地。
7. 运行时查询默认口径与统一 schema 命名一致（`governance/runtime/trust_meta/trust_data/audit`）。

## 6. 风险与缓解

1. 风险：观测写入放大导致主链路延迟。
- 缓解：异步写、批量写、限流；失败可见不可静默。

2. 风险：schema 漂移导致查询断裂。
- 缓解：统一迁移与契约测试，SQL 口径单一化。

3. 风险：告警噪声过多。
- 缓解：阈值分级、抑制窗口、人工 ack 闭环。
