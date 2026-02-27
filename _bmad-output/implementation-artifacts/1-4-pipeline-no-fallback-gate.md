# Story 1.4 - 地址治理流水线 No-Fallback Gate

Status: done

## 目标

保证地址流水线输入异常时 fail-fast，并将阻塞原因写入 worker/审计链路。

## Tasks

- [x] 空输入/空地址测试先失败
- [x] `pipeline.run` 输入契约拦截并抛 `blocked`
- [x] worker 捕获 `blocked` 写 `BLOCKED` 状态
- [x] worker 写 blocked 审计事件
- [x] 补充端到端失败回放场景验证

## 交付物

- `packages/address_core/pipeline.py`
- `services/governance_worker/app/jobs/governance_job.py`
- `services/governance_worker/tests/test_governance_job_blocked_audit.py`
