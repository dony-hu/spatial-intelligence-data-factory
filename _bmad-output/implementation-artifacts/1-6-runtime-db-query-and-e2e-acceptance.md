# Story 1.6 - Runtime/DB 查询与端到端验收

Status: done

## 目标

补齐 Runtime/DB 查询接口与端到端验收脚本，形成可复现的“发布-查询-阻塞审批”全链路证据。

## Tasks

- [x] 增加发布阻塞场景审计与审批链路端到端测试
- [x] 增加发布记录查询过滤/历史版本对比接口
- [x] 固化一键验收脚本与输出模板（JSON/Markdown）
- [x] 更新文档与 DoD 证据索引

## 预期交付物

- `services/governance_api/app/routers/ops.py`
- `services/governance_api/tests/test_workpackage_publish_e2e_flow.py`
- `tests/test_factory_agent_publish_blocked_audit.py`
- `scripts/run_address_governance_mvp_acceptance.py`
- `_bmad-output/implementation-artifacts/epic-1-dod-evidence.md`
