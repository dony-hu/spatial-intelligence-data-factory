# 真实数据库集成环境与治理看板 Spec

## Why
- 用户明确要求在真实数据库（Postgres）中运行并验证数据治理过程，并通过可观测性面板（Observability Dashboard）查看执行结果和数据前后对比。
- 当前 E2E 测试依赖内存模拟，无法满足 "实实在在的数据治理过程" 的验证需求。
- P0 级任务 `test_rulesets_postgres_integration.py` 失败，阻塞了真实数据库集成测试的推进。
- 现有看板缺乏针对 "地址治理" 业务数据的可视化展示。

## What Changes
- **新增基础设施**:
    - `docker-compose.yml`: PostgreSQL 15 + Redis 7。
    - `Makefile`: 集成环境启停、测试运行、看板更新命令。
- **修复 P0 测试**:
    - 修复 `services/governance_api/tests/test_rulesets_postgres_integration.py`，确保其在真实 DB 下通过。
- **增强 E2E 测试与报告**:
    - 修改 `tests/e2e/test_address_governance_full_cycle.py`，增加 `--report-json` 选项或自动输出结果到 `output/lab_mode/governance_e2e_latest.json`。
    - 测试逻辑中增加对真实数据库数据的持久化验证（非 cleanup 模式）。
- **新增治理指标采集**:
    - 创建 `scripts/collect_governance_metrics.py`，统计 `addr_raw` (总量), `addr_canonical` (治理后), `addr_task_run` (任务状态) 等核心指标，生成 `output/dashboard/governance_metrics.json`。
- **看板前端更新**:
    - 创建 `output/dashboard/governance_dashboard.html`，集成：
        - E2E 测试执行状态（来自 `test_status_board.json` 或 `governance_e2e_latest.json`）。
        - 核心治理指标（Raw vs Canonical 数量对比、任务成功率）。
        - 治理前后的数据样例展示（Top 5）。

## Impact
- **Affected specs**: `system-status-planning`, `address-governance-e2e-suite`.
- **Affected code**:
    - `docker-compose.yml` (New)
    - `Makefile` (New)
    - `services/governance_api/tests/test_rulesets_postgres_integration.py`
    - `tests/e2e/test_address_governance_full_cycle.py`
    - `scripts/collect_governance_metrics.py` (New)
    - `output/dashboard/governance_dashboard.html` (New)

## ADDED Requirements
### Requirement: Real DB Infrastructure
- **WHEN** 运行 `make up`
- **THEN** 启动 Postgres 和 Redis，并暴露端口。

### Requirement: Governance Metrics Visualization
- **WHEN** 打开 `governance_dashboard.html`
- **THEN** 展示：
    - E2E 测试通过率。
    - 数据库中 `addr_raw` 和 `addr_canonical` 的总记录数。
    - 最近一次治理任务的详细数据（输入 vs 输出）。

## MODIFIED Requirements
### Requirement: Postgres Integration Test
- **WHEN** 运行 `make test-integration`
- **THEN** `test_rulesets_postgres_integration.py` 必须通过。
