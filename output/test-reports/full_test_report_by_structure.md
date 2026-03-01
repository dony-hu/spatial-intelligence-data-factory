# 全量测试报告（按目录结构）

生成时间：2026-03-01 10:37:42 

## 执行口径
- 命令：`PYTHONPATH=. pytest -q --maxfail=0 --ignore=tests/test_continuous_demo_cleanup.py`
- 环境：加载 `config/database.postgres.env` 的 PG DSN；禁止 fallback。
- 说明：`tests/test_continuous_demo_cleanup.py` 在收集阶段导入失败（`tools.factory_simple_server` 缺少 `start_server`），因此被单独标记为阻塞项。

- services/governance_api/tests：总计 99，通过 91，失败 8，错误 0，跳过 0，通过率 91.9%
- services/governance_worker/tests：总计 11，通过 11，失败 0，错误 0，跳过 0，通过率 100.0%
- services/trust_data_hub/tests：总计 13，通过 1，失败 12，错误 0，跳过 0，通过率 7.7%
- packages/address_core/tests：总计 23，通过 23，失败 0，错误 0，跳过 0，通过率 100.0%
- packages/agent_runtime/tests：总计 13，通过 13，失败 0，错误 0，跳过 0，通过率 100.0%
- tests/e2e：总计 4，通过 1，失败 3，错误 0，跳过 0，通过率 25.0%
- tests/web_e2e：总计 6，通过 1，失败 0，错误 5，跳过 0，通过率 16.7%
- tests：总计 157，通过 145，失败 12，错误 0，跳过 0，通过率 92.4%

## 总体结果
- 总计：326
- 通过：286
- 失败：35
- 错误：5
- 跳过：0

## 阻塞项
- `tests/test_continuous_demo_cleanup.py`：导入 `start_server` 失败，导致“完整不忽略”的全量执行在收集阶段中断。

## 失败/错误样例（前20）
- [services/governance_api/tests] `services/governance_api/tests/test_lab_api.py::test_lab_optimize_creates_pending_change_request` -> assert 404 == 200
- [services/governance_api/tests] `services/governance_api/tests/test_ops_sql_readonly_api.py::test_readonly_sql_query_accepts_select_with_limit_and_audit` -> assert False
- [services/governance_api/tests] `services/governance_api/tests/test_ops_sql_readonly_api.py::test_readonly_sql_query_rejects_non_whitelisted_table` -> assert False
- [services/governance_api/tests] `services/governance_api/tests/test_rulesets_api.py::test_change_request_and_activation_hard_gate` -> assert 404 == 200
- [services/governance_api/tests] `services/governance_api/tests/test_rulesets_api.py::test_activate_ruleset_rejects_unknown_change_request` -> services.governance_api.app.repositories.governance_repository.GovernanceGateError: change request not found
- [services/governance_api/tests] `services/governance_api/tests/test_rulesets_postgres_integration.py::test_activate_ruleset_requires_approved_change_request_postgres` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.WrongObjectType) cannot create index on relation "addr_workpackage_publish"
- [services/governance_api/tests] `services/governance_api/tests/test_runtime_workpackage_real_chain_from_factory_agent.py::test_runtime_pipeline_observable_from_factory_agent_publish` -> assert None is not None
- [services/governance_api/tests] `services/governance_api/tests/test_workpackage_publish_e2e_flow.py::test_agent_publish_then_query_api_end_to_end` -> AssertionError: assert 'blocked' == 'ok'
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_hub_api.py::test_four_buttons_workflow_and_audit_chain` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "trust_meta.source_registry" does not exist
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_hub_api.py::test_publish_requires_validation` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "trust_meta.source_registry" does not exist
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_hub_api.py::test_query_and_validation_api_include_evidence_refs` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "trust_meta.source_registry" does not exist
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_hub_api.py::test_high_diff_requires_manual_confirmation` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "trust_meta.source_registry" does not exist
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_hub_api.py::test_namespace_isolation_for_query` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "trust_meta.source_registry" does not exist
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_hub_api.py::test_phase1_schedule_and_reports_and_replay` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "trust_meta.source_registry" does not exist
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_hub_api.py::test_phase2_bootstrap_sample_sources` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "trust_meta.source_registry" does not exist
- [tests/web_e2e] `tests/web_e2e/test_lab_replay_ui.py::test_lab_replay_page_renders_core_sections` -> failed on setup with "urllib.error.HTTPError: HTTP Error 404: Not Found"
- [tests/web_e2e] `tests/web_e2e/test_lab_replay_ui.py::test_lab_replay_page_reflects_approval_and_activation_path` -> failed on setup with "urllib.error.HTTPError: HTTP Error 404: Not Found"
- [tests/web_e2e] `tests/web_e2e/test_observability_live_ui.py::test_observability_live_page_renders_core_sections` -> failed on setup with "file /Users/01411043/code/spatial-intelligence-data-factory/tests/web_e2e/test_observability_live_ui.py, line 7
- [tests/web_e2e] `tests/web_e2e/test_observability_live_ui.py::test_observability_live_page_updates_connection_state` -> failed on setup with "file /Users/01411043/code/spatial-intelligence-data-factory/tests/web_e2e/test_observability_live_ui.py, line 20
- [tests/web_e2e] `tests/web_e2e/test_runtime_observability_upload_ui.py::test_runtime_observability_upload_batch_from_csv` -> failed on setup with "file /Users/01411043/code/spatial-intelligence-data-factory/tests/web_e2e/test_runtime_observability_upload_ui.py, line 12