# Address Topology v1.0.1 / v1.0.2 Acceptance Pack

Generated at: 2026-02-15 20:08 CST

## 1) Acceptance Checklist

### wp-address-topology-v1.0.1
- [x] input_contract 与 v1.0.2 对齐（`raw_address`, `task_id`）
- [x] process_spec 固定四步：`parse -> normalize -> validate -> topology_build`
- [x] 规则口径固定：`quality_score >= 0.95` 才视为成功
- [x] 增加 `line_feedback_contract`（failure/replay sqlite ref）
- [x] 输出契约兼容 v1.0.2（新增可选 trace/ref 字段）

### wp-address-topology-v1.0.2
- [x] 输入/输出契约稳定
- [x] line_feedback_contract 固定引用规则
- [x] 失败回放可追溯约束存在
- [x] engine 兼容窗口声明存在（1.0.0 ~ 1.1.x）

## 2) Diff Summary (v1.0.1 -> v1.0.2)

- v1.0.2 新增/强化：
  - `factory_release.rollback_target_version`
  - `factory_release.runtime_record_ref`
  - `engine_bundle.compatibility`
  - line goal 明确包含失败回放证据回传
- 本次收敛后，两版本公共口径保持一致：
  - 算法顺序一致
  - 质量阈值一致
  - line feedback sqlite ref 一致

## 3) Reproducible Demo Samples

- 固定样本定义：
  - `workpackages/bundles/address-topology-v1.0.2/demo/fixed_demo_samples.v1.json`
- 成功样本（历史可复现基线）：
  - `output/line_runs/tc06_single_run_2026-02-14_114036_180784.json` (`status=completed`)
- 失败样本（最新实跑）：
  - `output/line_runs/tc06_single_run_2026-02-15_200707_733516.json` (`status=failed`)
  - `output/line_runs/tc06_single_run_2026-02-15_200707_746090.json` (`status=failed`)
- 回放样本（最新实跑）：
  - `output/line_runs/tc06_failure_replay_2026-02-15_200716_718064.json`
- 最新产线回传：
  - `output/workpackages/line_feedback.address_topology.latest.json`

## 4) Rollback Plan (Executable)

1. 停止新任务注入。
2. 将执行入口 workpackage 固定回退：
   - 从 `wp-address-topology-v1.0.2.json` 切回 `wp-address-topology-v1.0.1.json`。
3. 使用 `line_feedback_contract` 指定的 sqlite 引用执行失败队列回放，并比对质量结果。
4. 若回放后质量仍不达标（`quality_score < 0.95` 或恢复率不满足目标），继续回退到 `v1.0.0`。

## 5) Current Gate Snapshot

- Unit/contract tests: PASS
- Schema validation for v1.0.1/v1.0.2: PASS
- Runtime unified 3.11+: FAIL on this host (current runtime is 3.9)
- Decision on this host: NO_GO (env blocker only)
