# Story：TEST-E2E-S3 Runtime审批回滚与人工介入链路E2E补齐

## 状态

待开始

## 目标

补齐 Runtime 状态机中审批、回滚和人工介入分支的 E2E 设计。

## 验收标准

1. 至少覆盖 `APPROVAL_PENDING -> APPROVED -> CHANGESET_READY`。
2. 至少覆盖一条 `ROLLED_BACK` 场景。
3. 至少覆盖一条 `NEEDS_HUMAN` 场景，并包含恢复或终止分支。
4. 每条用例都同时断言状态、证据和审计对象。

## 交付物

1. `docs/09_测试与验收/全链路测试设计.md` 中的详细设计补充
2. 对应自动化实现任务清单
