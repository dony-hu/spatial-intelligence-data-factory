# Story 2.1 证据索引 - 可观测性与 PG 基础

## 已交付能力

1. 观测基础模型：event / metric / alert。
2. 观测 API：snapshot / events / timeseries / trace replay / alerts ack。
3. trace_id 贯通：task submit -> queue -> worker -> result。
4. `lab/observability` 管理数据契约补充 `observation_foundation`。
5. 一键验收脚本（JSON + Markdown）。

## 关键代码

- `services/governance_api/app/models/observability_models.py`
- `services/governance_api/app/routers/observability.py`
- `services/governance_api/app/repositories/governance_repository.py`
- `services/governance_api/app/routers/tasks.py`
- `services/governance_worker/app/jobs/governance_job.py`
- `services/governance_api/app/routers/lab.py`
- `database/postgres/sql/002_init_tables.sql`
- `database/postgres/sql/003_init_indexes.sql`
- `scripts/init_governance_sqlite.py`
- `migrations/versions/20260227_0003_unified_schema_alignment.py`
- `scripts/init_governance_pg_schema.py`（默认阻塞 legacy DDL）
- `scripts/init_unified_pg_schema.py`（默认阻塞 legacy DDL）

## 验证测试

- `services/governance_api/tests/test_observability_foundation_api.py`
- `services/governance_api/tests/test_observability_integration.py`
- `tests/test_observability_foundation_acceptance_script.py`
- `services/governance_api/tests/test_lab_api.py`（observability 契约）
- `tests/test_legacy_ddl_scripts_blocked.py`

## 验收产物

- `scripts/run_observability_pg_foundation_acceptance.py`
- `output/acceptance/observability-pg-foundation-acceptance-20260227-043350.json`
- `output/acceptance/observability-pg-foundation-acceptance-20260227-043350.md`
