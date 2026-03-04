# Story 3.7 - 地址治理质量漂移与异常检测

Status: done

## 目标

建立治理质量漂移检测能力，提前发现模型/规则/数据源变化导致的质量退化。

## Tasks

- [x] T1: 先补失败用例（TDD）
- [x] T1.1: 新增质量指标计算失败用例
- [x] T1.2: 新增漂移阈值检测失败用例
- [x] T1.3: 新增异常下钻联动失败用例
- [x] T2: 实现质量漂移检测器与 API
- [x] T2.1: 实现 7d 基线与窗口对比逻辑
- [x] T2.2: 实现异常告警触发与返回
- [x] T2.3: 质量检测失败返回显式错误
- [x] T3: 回归与验证
- [x] T3.1: 运行质量漂移契约回归
- [x] T3.2: 运行运行态可观测回归矩阵

## 验收标准

1. 质量指标支持按时间窗稳定查询。
2. 可识别突增/突降漂移异常。
3. 异常点可关联样本任务下钻。
4. 版本对比可输出提升/退化结论。
5. 检测失败显式报错，不静默忽略。

## Dev Agent Record

### Completion Notes

- 已通过 `test_runtime_quality_drift.py` 与运行态回归矩阵，验证质量漂移检测与异常告警链路可用。

## File List

- services/governance_api/app/services/governance_service.py
- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_quality_drift.py
- _bmad-output/implementation-artifacts/3-7-address-governance-quality-drift-and-anomaly-detection.md

## Change Log

- 2026-03-02: 执行 `W-DEV` 推进 Story 3.7 至 `done`，补齐实现工件与验证记录。
