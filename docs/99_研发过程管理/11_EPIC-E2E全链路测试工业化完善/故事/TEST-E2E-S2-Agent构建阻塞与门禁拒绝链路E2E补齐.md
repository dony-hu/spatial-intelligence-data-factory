# Story：TEST-E2E-S2 Agent构建阻塞与门禁拒绝链路E2E补齐

## 状态

待开始

## 目标

补齐当前 E2E 中缺失的 Agent 构建阻塞、用户补充恢复和门禁拒绝链路。

## 验收标准

1. 至少覆盖 `API_AUTH_MISSING`、`DEPENDENCY_MISSING`、`CAPABILITY_GAP` 三类构建阻塞。
2. 至少覆盖一条 `WAIT_USER_GATE -> BLOCKED` 的人工拒绝或主动中止场景。
3. 所有场景都写明恢复点和责任域。

## 交付物

1. `docs/09_测试与验收/全链路测试设计.md` 中的详细设计补充
2. 对应自动化实现任务清单
