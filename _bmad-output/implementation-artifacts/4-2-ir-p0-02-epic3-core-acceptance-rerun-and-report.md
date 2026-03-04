# Story 4.2 - IR-P0-02 Epic3 核心验收重跑与报告固化

Status: ready-for-dev

## 目标

重跑 Epic3 核心验收矩阵并固化单一报告，形成可用于 Go/No-Go 的统一证据包。

## 验收标准

1. 覆盖 pipeline/events/llm/rbac/upload-batch 的核心接口测试。
2. 覆盖 Web E2E 最小链路（至少工作包链路面板与上传入口）。
3. 报告同时包含：测试命令、通过/失败结果、失败归因、No-Fallback 验证结论。
4. 任一关键测试失败时输出 `NO_GO` 建议并显式阻断，不允许 fallback 通过。

## Tasks

- [ ] T1: 先补失败用例（TDD）
- [ ] T1.1: 新增“报告字段缺失”失败用例（缺命令/结论/风险时失败）
- [ ] T1.2: 新增“关键模块未覆盖”失败用例（pipeline/events/llm/rbac/upload-batch）
- [ ] T1.3: 新增“关键失败仍给 GO”失败用例

- [ ] T2: 实现验收重跑编排
- [ ] T2.1: 固化核心测试集合与执行顺序
- [ ] T2.2: 生成统一回归报告（单份）
- [ ] T2.3: 失败路径明确输出 `NO_GO` 语义，禁止 fallback

- [ ] T3: 回归与证据固化
- [ ] T3.1: 执行核心矩阵并保存结果
- [ ] T3.2: 更新 `docs/acceptance/` 与 `output/test-reports/` 汇总文件

## 测试命令（建议）

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py \
  services/governance_api/tests/test_runtime_workpackage_events_api_contract.py \
  services/governance_api/tests/test_runtime_llm_interactions_api_contract.py \
  services/governance_api/tests/test_runtime_workpackage_observability_rbac.py \
  services/governance_api/tests/test_runtime_upload_batch.py
```

## File List（预期）

- output/test-reports/epic-3-regression-summary-*.md
- docs/acceptance/epic3-full-acceptance-*.json
- docs/acceptance/epic3-full-acceptance-*.md
- _bmad-output/implementation-artifacts/4-2-ir-p0-02-epic3-core-acceptance-rerun-and-report.md

## 证据路径

- output/test-reports/epic-3-regression-summary-*.md
- docs/acceptance/epic3-full-acceptance-*.json
- docs/acceptance/epic3-full-acceptance-*.md

