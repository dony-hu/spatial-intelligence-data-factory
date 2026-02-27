# Story 1.1 - CLI-Agent-LLM 需求确认

Status: done

## 目标

打通 CLI -> Session -> Agent -> LLM 的需求确认链路，并在 LLM 不可用时阻塞流程，不允许 fallback。

## Tasks

- [x] 增加 LLM 阻塞语义测试（blocked）
- [x] 移除运行时 fallback 逻辑，改为 fail-fast
- [x] CLI 在 blocked/error 时返回非零退出码
- [x] 回归验证并输出测试结果

## 交付物

- `packages/agent_runtime/adapters/opencode_runtime.py`
- `packages/factory_agent/agent.py`
- `packages/factory_cli/session.py`
- `scripts/factory_cli.py`
