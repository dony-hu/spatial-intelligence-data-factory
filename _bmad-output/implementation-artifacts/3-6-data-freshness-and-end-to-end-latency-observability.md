# Story 3.6 - 数据新鲜度与端到端延迟观测

Status: done

## 目标

建立从任务提交到页面展示的端到端时延可观测能力，定位“页面有数据但不及时”的问题。

## Tasks

- [x] T1: 先补失败用例（TDD）
- [x] T1.1: 新增延迟指标计算失败用例（event/aggregation/data_age）
- [x] T1.2: 新增阈值告警失败用例
- [x] T1.3: 新增页面新鲜度字段契约失败用例
- [x] T2: 实现延迟观测链路
- [x] T2.1: 实现新鲜度/延迟汇总 API
- [x] T2.2: 实现阈值评估与告警触发
- [x] T2.3: 数据源异常返回显式错误语义
- [x] T3: 回归与证据归档
- [x] T3.1: 运行后端契约回归
- [x] T3.2: 运行运行态可观测回归矩阵

## 验收标准

1. `event_lag_seconds/aggregation_lag_seconds/dashboard_data_age_seconds` 可查询。
2. 超阈值可触发告警并返回触发列表。
3. 可区分 ingestion/aggregation/query 层级问题。
4. 页面端可显示最近更新时间。
5. 数据源不可用时返回显式错误，不回退虚假数据。

## Dev Agent Record

### Completion Notes

- 已通过 `test_runtime_freshness_latency.py` 与运行态回归矩阵，验证新鲜度与端到端延迟能力可用。

## File List

- services/governance_api/app/services/governance_service.py
- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_freshness_latency.py
- _bmad-output/implementation-artifacts/3-6-data-freshness-and-end-to-end-latency-observability.md

## Change Log

- 2026-03-02: 执行 `W-DEV` 推进 Story 3.6 至 `done`，补齐实现工件与验证记录。
