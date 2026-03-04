# Story 3.4 - 任务下钻追溯与回归验收闭环

Status: done

## Tasks

- [x] 任务下钻返回输入/输出/evidence/review/trace
- [x] 补齐追溯链路契约测试
- [x] 回归并沉淀验收闭环证据

## 验收标准

1. 任一任务可下钻到证据链。
2. Trace 字段完整并可回放。
3. 回归报告可用于发布判定。

## 测试命令

```bash
PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_events_api_contract.py
```

## File List

- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_workpackage_events_api_contract.py

## 证据路径

- docs/acceptance/s2-14-runtime-observability-acceptance-2026-03-01.md
