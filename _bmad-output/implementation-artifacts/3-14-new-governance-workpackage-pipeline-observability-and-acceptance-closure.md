# Story 3.14 - 新增治理包链路观测与验收闭环

Status: done

## Tasks

- [x] 落地 `workpackage-pipeline/workpackage-events/llm-interactions` 三类接口
- [x] 补齐 RBAC 脱敏差异与 receipt 字段校验
- [x] 产出 MVP 验收证据

## 验收标准

1. 页面可查看完整治理包链路和 runtime receipt。
2. viewer/admin 在 LLM 交互详情上权限与脱敏差异正确。
3. 契约测试通过并有文档证据。

## 测试命令

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py \
  services/governance_api/tests/test_runtime_workpackage_events_api_contract.py \
  services/governance_api/tests/test_runtime_llm_interactions_api_contract.py \
  services/governance_api/tests/test_runtime_workpackage_observability_rbac.py
```

## File List

- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py
- services/governance_api/tests/test_runtime_workpackage_events_api_contract.py
- services/governance_api/tests/test_runtime_llm_interactions_api_contract.py
- services/governance_api/tests/test_runtime_workpackage_observability_rbac.py

## 证据路径

- docs/acceptance/s2-14-runtime-observability-acceptance-2026-03-01.json
- docs/acceptance/s2-14-runtime-observability-acceptance-2026-03-01.md
