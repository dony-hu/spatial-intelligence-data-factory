# Story：OBS-RUNTIME-S2-11 No-Fallback 默认门禁与测试口径收敛

## 1. 目标

将测试主线默认切换为 No-Fallback（`fallback=0`），确保测试通过即代表 PG 真实链路可用。

## 2. 范围

1. 主线测试移除默认 `GOVERNANCE_ALLOW_MEMORY_FALLBACK=1`。
2. 仅隔离测试允许 fallback，并要求显式标记（如 `@pytest.mark.fallback_isolated`）。
3. 增加 CI 门禁：主线测试出现 fallback 默认开启即失败。

## 3. 验收标准

1. 主线测试默认在 `fallback=0` 下通过。
2. fallback 用例有清单、有标记、有说明。
3. 验收报告可区分“真实链路通过”与“隔离测试通过”。

## 4. 测试要求（TDD）

1. 先补门禁失败用例。
2. 再批量调整测试环境变量策略。
3. 最后跑主线回归并输出差异报告。
