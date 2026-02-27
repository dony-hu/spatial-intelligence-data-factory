# Epic 1 DoD 证据索引（地址治理 MVP）

## 目标范围

- CLI ↔ Agent ↔ LLM 交互链路（No-Fallback）
- Dry Run / Publish / Runtime 查询
- 阻塞审计与人工确认链路
- Trust Hub 能力沉淀与样例持久化

## 关键代码与接口

- `packages/factory_agent/agent.py`
- `services/governance_api/app/repositories/governance_repository.py`
- `services/governance_api/app/routers/ops.py`
- `services/governance_worker/app/jobs/governance_job.py`
- `packages/trust_hub/__init__.py`

## 验证用例（核心）

- `services/governance_api/tests/test_workpackage_publish_repository.py`
- `services/governance_api/tests/test_workpackage_publish_api.py`
- `services/governance_api/tests/test_workpackage_publish_e2e_flow.py`
- `tests/test_factory_agent_publish_blocked_audit.py`
- `tests/test_mvp_acceptance_script.py`
- `tests/test_trust_hub_trustdb_query.py`
- `services/governance_worker/tests/test_governance_job_no_fallback_gate.py`
- `services/governance_worker/tests/test_governance_job_blocked_audit.py`
- `packages/address_core/tests/test_pipeline_no_fallback.py`

## 验收脚本与输出模板

- 验收脚本：`scripts/run_address_governance_mvp_acceptance.py`
- 标准输入校验：`scripts/validate_bmad_story_deliver_inputs.py`
- 产出目录：`output/acceptance/`
- 产出样例：
  - `output/acceptance/address-governance-mvp-acceptance-20260227-040204.json`
  - `output/acceptance/address-governance-mvp-acceptance-20260227-040204.md`

## 回归结果

- 关键回归：`37 passed in 24.32s`
- 增量回归（含 TrustHub trust_meta/trust_db 查询验证）：`24 passed in 24.16s`
- 验收脚本执行成功并输出 JSON + Markdown 双格式证据
