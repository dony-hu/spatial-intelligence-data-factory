# Story 4.3 - IR-P0-03 运行阶段枚举字典统一

Status: ready-for-dev

## 目标

统一运行阶段枚举字典（含 `dryrun_finished/publish_confirmed`），并对齐 API、UI、测试三端口径。

## 验收标准

1. API 响应字段中的阶段枚举仅来自单一字典定义。
2. UI 展示与 API 枚举一致，不出现旧枚举别名混用。
3. 测试断言与字典一致（移除 S2-14/S2-15 口径漂移）。
4. 遇到未知枚举时显式错误（`blocked/error`），不回退默认值。

## Tasks

- [ ] T1: 先补失败用例（TDD）
- [ ] T1.1: 新增 API 枚举不一致失败用例
- [ ] T1.2: 新增 UI 枚举映射缺失失败用例
- [ ] T1.3: 新增未知枚举处理失败用例（应显式报错）

- [ ] T2: 实现字典统一
- [ ] T2.1: 提取并固定运行阶段字典（单点定义）
- [ ] T2.2: API 与 UI 统一消费该字典
- [ ] T2.3: 测试断言更新并覆盖异常路径

- [ ] T3: 回归与证据固化
- [ ] T3.1: 执行契约/UI 关键回归
- [ ] T3.2: 输出字典映射与兼容说明

## 测试命令（建议）

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py \
  services/governance_api/tests/test_runtime_workpackage_events_api_contract.py \
  tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py
```

## File List（预期）

- services/governance_api/app/services/governance_service.py
- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py
- services/governance_api/tests/test_runtime_workpackage_events_api_contract.py
- _bmad-output/implementation-artifacts/4-3-ir-p0-03-runtime-stage-enum-dictionary-unification.md

## 证据路径

- docs/acceptance/epic3-full-acceptance-*.md
- output/test-reports/epic-3-regression-summary-*.md

