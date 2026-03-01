# 全量测试报告（P0修复后）

生成时间：2026-03-01 11:30:29 

## 执行命令
- `PYTHONPATH=. pytest -q --maxfail=0 --junitxml=output/test-reports/full_pytest_junit_after_p0fix.xml`

## 分层结果
- services/governance_api/tests：总计 99，通过 91，失败 8，错误 0，跳过 0，通过率 91.9%
- services/governance_worker/tests：总计 11，通过 11，失败 0，错误 0，跳过 0，通过率 100.0%
- services/trust_data_hub/tests：总计 13，通过 12，失败 1，错误 0，跳过 0，通过率 92.3%
- packages/address_core/tests：总计 23，通过 23，失败 0，错误 0，跳过 0，通过率 100.0%
- packages/agent_runtime/tests：总计 13，通过 13，失败 0，错误 0，跳过 0，通过率 100.0%
- tests/e2e：总计 4，通过 1，失败 3，错误 0，跳过 0，通过率 25.0%
- tests/web_e2e：总计 6，通过 6，失败 0，错误 0，跳过 0，通过率 100.0%
- tests：总计 158，通过 143，失败 15，错误 0，跳过 0，通过率 90.5%

## 总体
- 总计：327
- 通过：300
- 失败：27
- 错误：0
- 跳过：0

## 关键进展
- `tests/test_continuous_demo_cleanup.py` 导入阻塞已修复并通过。
- `services/trust_data_hub/tests/test_trust_data_hub_api.py` 已全通过（12/12）。
- `tests/web_e2e` 已全通过（6/6），`lab/optimize` 404 和 Playwright 依赖问题已解除。

## 当前剩余失败（前20）
- [services/governance_api/tests] `services/governance_api/tests/test_ops_sql_readonly_api.py::test_readonly_sql_query_accepts_select_with_limit_and_audit` -> assert False
- [services/governance_api/tests] `services/governance_api/tests/test_ops_sql_readonly_api.py::test_readonly_sql_query_rejects_non_whitelisted_table` -> assert False
- [services/governance_api/tests] `services/governance_api/tests/test_repository_pg_only_path_in_pg_mode.py::test_get_review_and_ruleset_use_pg_only_path_in_pg_mode` -> AssertionError: assert {'ruleset_id': 'rule-x'} is None
- [services/governance_api/tests] `services/governance_api/tests/test_rulesets_api.py::test_change_request_and_activation_hard_gate` -> services.governance_api.app.repositories.governance_repository.GovernanceGateError: change request is not approved
- [services/governance_api/tests] `services/governance_api/tests/test_rulesets_api.py::test_activate_ruleset_rejects_unknown_change_request` -> services.governance_api.app.repositories.governance_repository.GovernanceGateError: change request not found
- [services/governance_api/tests] `services/governance_api/tests/test_rulesets_postgres_integration.py::test_activate_ruleset_requires_approved_change_request_postgres` -> sqlalchemy.exc.ProgrammingError: (psycopg2.errors.WrongObjectType) cannot create index on relation "addr_workpackage_publish"
- [services/governance_api/tests] `services/governance_api/tests/test_runtime_workpackage_real_chain_from_factory_agent.py::test_runtime_pipeline_observable_from_factory_agent_publish` -> assert None is not None
- [services/governance_api/tests] `services/governance_api/tests/test_workpackage_publish_e2e_flow.py::test_agent_publish_then_query_api_end_to_end` -> AssertionError: assert 'blocked' == 'ok'
- [services/trust_data_hub/tests] `services/trust_data_hub/tests/test_trust_data_schema_naming_guard.py::test_trustdb_persister_uses_trust_data_schema` -> assert 'trust_db.' not in 'from __futu...r in rows]\n'
- [tests/e2e] `tests/e2e/test_address_governance_full_cycle.py::test_happy_path_clean_address` -> AssertionError: assert 'FAILED' == 'SUCCEEDED'
- [tests/e2e] `tests/e2e/test_address_governance_full_cycle.py::test_manual_review_flow` -> assert 0 == 1
- [tests/e2e] `tests/e2e/test_address_governance_full_cycle.py::test_concurrent_batch_submissions` -> AssertionError: assert 'FAILED' == 'SUCCEEDED'
- [tests] `tests/test_factory_agent_publish_blocked_audit.py::test_publish_blocked_should_log_blocked_confirmation_audit` -> AssertionError: assert 3431 >= (3431 + 1)
- [tests] `tests/test_factory_agent_publish_runtime.py::test_publish_success_with_version_and_evidence` -> AssertionError: assert 'blocked' == 'ok'
- [tests] `tests/test_factory_agent_publish_runtime.py::test_publish_blocked_when_runtime_execution_failed` -> assert None is not None
- [tests] `tests/test_factory_agent_trust_hub_mvp.py::test_supplement_trust_hub_returns_capability_and_sample` -> AssertionError: assert 'blocked' == 'ok'
- [tests] `tests/test_factory_process_expert_short_path/FactoryProcessExpertShortPathTests.py::test_real_mode_llm_and_map_api` -> AssertionError: None != '1' : FACTORY_REAL_SHORT_PATH=1 is required
- [tests] `tests/test_mvp_acceptance_pipeline_split.py::test_mvp_acceptance_unit_script_runs_with_real_gate` -> AssertionError: Acceptance JSON: /private/var/folders/ly/16mz3gsd79x4g1c4y87r98f8gr4tlw/T/pytest-of-01411043/pytest-19/test_mvp_acceptance_unit_scrip0/output/acceptance/address-gov
- [tests] `tests/test_mvp_acceptance_script.py::test_run_acceptance_script_as_subprocess` -> AssertionError: Acceptance JSON: /private/var/folders/ly/16mz3gsd79x4g1c4y87r98f8gr4tlw/T/pytest-of-01411043/pytest-19/test_run_acceptance_script_as_0/output/acceptance/address-gov
- [tests] `tests/test_next_iteration_gaps/TestNextIterationGaps.py::test_output_persist_generator_uses_runtime_table_name` -> AssertionError: '{self.table_name}' not found in '"""\n数据库持久化器 - 自动生成\nDomain: address_governance\n参数: {\'table_name\': \'x\'}\n"""\n\nfrom typing import List, Dict, Any\n\n\nclass