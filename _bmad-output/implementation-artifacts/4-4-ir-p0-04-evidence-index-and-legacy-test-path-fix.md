# Story 4.4 - IR-P0-04 证据索引映射与旧测试路径修正

Status: ready-for-dev

## 目标

修正文档中失效测试路径，产出统一“证据索引映射表”，保证会签可追溯且可复核。

## 验收标准

1. 关键文档中不再引用不存在的测试文件路径。
2. 证据索引映射表覆盖：测试文件 -> 验收报告 -> 工件路径。
3. 映射表中的每条路径可被脚本校验存在。
4. 路径缺失时显式失败（`blocked/error`），不允许静默忽略。

## Tasks

- [ ] T1: 先补失败用例（TDD）
- [ ] T1.1: 新增“文档引用失效路径”检测失败用例
- [ ] T1.2: 新增“证据映射缺项”失败用例
- [ ] T1.3: 新增“路径存在性校验”失败用例

- [ ] T2: 实现文档与映射修复
- [ ] T2.1: 扫描并修正文档中的旧测试路径
- [ ] T2.2: 生成证据索引映射表（含来源与校验状态）
- [ ] T2.3: 未通过校验时返回 `blocked/error` 并阻断会签

- [ ] T3: 回归与证据固化
- [ ] T3.1: 执行文档路径校验脚本
- [ ] T3.2: 输出最终索引表与校验结果

## 测试命令（建议）

```bash
rg -n \"test_.*\\.py|output/test-reports|docs/acceptance\" docs _bmad-output/implementation-artifacts -S
```

## File List（预期）

- docs/epic-runtime-observability-v2-review-2026-03-02.md
- docs/epic-runtime-observability-v2-retrospective-2026-03-02.md
- _bmad-output/implementation-artifacts/epic3-status-review-and-task-list-2026-03-02.md
- _bmad-output/implementation-artifacts/epic3-linear-pr-mapping-2026-03-02.md
- _bmad-output/implementation-artifacts/4-4-ir-p0-04-evidence-index-and-legacy-test-path-fix.md

## 证据路径

- _bmad-output/implementation-artifacts/epic3-linear-pr-mapping-2026-03-02.md
- docs/acceptance/epic3-full-acceptance-2026-03-02.md
- output/test-reports/epic-3-regression-summary-2026-03-02.md

