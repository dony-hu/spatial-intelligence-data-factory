# Story 3.1 - 运行态聚合 API 与指标口径统一

Status: done

## Tasks

- [x] 统一 `summary/risk-distribution/version-compare/tasks` 口径到后端聚合层
- [x] 固化核心字段契约并补充失败用例
- [x] 完成 API 契约回归并产出证据

## 验收标准

1. 关键 KPI 由后端统一计算，前端不私算核心指标。
2. 运行态 API 契约测试稳定通过。
3. 口径定义可追溯到 PRD/Architecture。

## 测试命令

```bash
PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_observability_api_contract.py
```

## File List

- services/governance_api/app/services/governance_service.py
- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_observability_api_contract.py

## 证据路径

- docs/prd-runtime-observability-dashboard-2026-02-28.md
- docs/architecture/architecture-runtime-observability-v2-2026-02-28.md
