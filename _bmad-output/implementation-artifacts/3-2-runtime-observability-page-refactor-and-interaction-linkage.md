# Story 3.2 - 运行态可观测页面重构与交互联动

Status: done

## Tasks

- [x] 页面信息架构切换为运行态视角（KPI/风险/版本/明细）
- [x] 完成列表与下钻联动
- [x] 补齐页面渲染与联动测试

## 验收标准

1. 页面默认展示运行态结果，不展示研发过程指标。
2. 支持从汇总到任务/链路下钻。
3. 空态存在引导文案与后续操作入口。

## 测试命令

```bash
PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_observability_view.py
```

## File List

- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_observability_view.py

## 证据路径

- docs/prd-runtime-observability-dashboard-2026-02-28.md
- tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py
