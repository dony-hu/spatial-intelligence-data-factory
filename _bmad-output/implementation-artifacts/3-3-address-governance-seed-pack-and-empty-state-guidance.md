# Story 3.3 - 地址治理样例包灌入与空态引导

Status: done

## Tasks

- [x] 新增样例包灌入 API
- [x] 空态引导接入灌入入口
- [x] 完成种子数据契约测试

## 验收标准

1. 可一键灌入样例并在 24h 窗口可观测。
2. 空态不是空白页，能指引操作。
3. 灌入后 pipeline 数据可查询。

## 测试命令

```bash
PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_seed_demo.py
```

## File List

- services/governance_api/app/routers/observability.py
- services/governance_api/app/services/governance_service.py
- services/governance_api/tests/test_runtime_workpackage_seed_demo.py

## 证据路径

- docs/prd-runtime-observability-dashboard-2026-02-28.md
