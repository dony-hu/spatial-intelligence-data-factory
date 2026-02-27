# Story 1.2 - Dry Run 流程与阻塞门禁

Status: done

## 目标

补齐工作包 dry run 的输入/输出摘要与契约校验；缺失关键文件时必须 blocked。

## Tasks

- [x] 新增 dry run 成功/失败场景测试
- [x] 缺失 `workpackage.json` / `entrypoint` 时返回 blocked
- [x] 输出结构化 `dryrun` 摘要
- [x] 回归验证通过

## 交付物

- `packages/factory_agent/agent.py`
- `tests/test_factory_agent_dryrun_no_fallback.py`
