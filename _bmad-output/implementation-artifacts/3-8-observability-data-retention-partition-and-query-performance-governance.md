# Story 3.8 - 观测数据保留分区与查询性能治理

Status: done

## 目标

建立观测数据容量治理能力，保证可观测页面在数据增长后仍保持稳定响应。

## Tasks

- [x] T1: 先补失败用例（TDD）
- [x] T1.1: 新增性能门槛失败用例
- [x] T1.2: 新增分区查询正确性失败用例
- [x] T1.3: 新增归档回查失败用例
- [x] T2: 实现查询性能治理
- [x] T2.1: 实现性能摘要与阈值评估 API
- [x] T2.2: 慢查询告警触发与去重策略接入
- [x] T2.3: 保持 PG-only + Alembic 迁移约束
- [x] T3: 回归与验证
- [x] T3.1: 运行性能治理契约回归
- [x] T3.2: 运行运行态可观测回归矩阵

## 验收标准

1. 首屏聚合与下钻查询满足性能门槛。
2. 分区/归档策略可执行并支持回查。
3. 慢 SQL 风险可识别并触发告警。
4. 数据增长场景性能无明显退化。
5. 不引入旁路 DDL，迁移链路合规。

## Dev Agent Record

### Completion Notes

- 已通过 `test_runtime_performance_governance.py` 与运行态回归矩阵，验证性能治理能力可用。

## File List

- services/governance_api/app/services/governance_service.py
- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_performance_governance.py
- _bmad-output/implementation-artifacts/3-8-observability-data-retention-partition-and-query-performance-governance.md

## Change Log

- 2026-03-02: 执行 `W-DEV` 推进 Story 3.8 至 `done`，补齐实现工件与验证记录。
