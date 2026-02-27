# Story 1.3 - 工作包发布到 Runtime

Status: done

## 目标

实现工作包发布契约校验、发布证据落地，以及发布记录持久化。

## Tasks

- [x] 新增发布成功/失败测试
- [x] 发布前校验 `skills/observability/entrypoint/workpackage.json`
- [x] 持久化 `workpackage_id + version + status + evidence_ref`
- [x] 新增发布记录 API 查询

## 交付物

- `packages/factory_agent/agent.py`
- `services/governance_api/app/repositories/governance_repository.py`
- `services/governance_api/app/routers/ops.py`
- `services/governance_api/tests/test_workpackage_publish_api.py`
