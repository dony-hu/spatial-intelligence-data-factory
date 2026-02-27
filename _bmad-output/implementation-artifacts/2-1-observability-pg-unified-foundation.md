# Story 2.1 - 可观测性与 PG 库一体化基础建设

Status: done

## 目标

将系统可观测性能力与 PG 库建设合并为一个可执行 Story，建立统一事件模型、统一存储、统一查询与统一告警闭环。

主规范（强制）：`docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`

## Tasks

- [x] 新增观测核心数据模型（event/metric/alert）并定义 PG 表结构
- [x] 实现观测查询 API（snapshot/events/timeseries/trace replay/alert ack）
- [x] 打通 CLI/Agent/API/Worker/Core 统一 trace_id 关联链路
- [x] 建立 No-Fallback 观测门禁（异常必须 blocked/error + 审计）
- [x] 升级 `lab/observability` 数据契约与最小看板
- [x] 增加一键验收脚本（JSON/Markdown）并固化 DoD 证据索引
- [x] schema 命名收敛至 `governance/runtime/trust_meta/trust_data/audit`
- [x] DDL 路径收敛为 Alembic 单入口（禁止新增并行生产 DDL）

## 交付物

- `docs/epic-observability-pg-unified-2026-02-27.md`
- `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`
- `docs/architecture-observability-capability-2026-02-27.md`
- `services/governance_api/app/routers/*`（观测查询接口）
- `services/governance_api/app/repositories/*`（观测持久化与聚合）
- `services/governance_worker/app/*`（观测埋点）
- `services/governance_api/tests/*` 与 `tests/*`（TDD 测试）
- `scripts/run_observability_pg_foundation_acceptance.py`
- `_bmad-output/implementation-artifacts/2-1-observability-pg-foundation-evidence.md`
