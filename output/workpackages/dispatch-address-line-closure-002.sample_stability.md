# Dispatch Address Line Closure 002 - Sample Stability

- batch_id: dispatch-address-line-closure-002
- sample_count: 10
- passed: 0
- failed: 10
- pass_rate: 0.0
- failure_categories: {'CLEANING_INVALID_OUTPUT': 10}

## Fixed Demo Samples
- success: `/Users/huda/Code/spatial-intelligence-data-factory/output/line_runs/tc06_single_run_2026-02-14_114036_180784.json`
- failure: `/Users/huda/Code/spatial-intelligence-data-factory/output/line_runs/tc06_single_run_2026-02-15_210228_402132.json`
- replay: `/Users/huda/Code/spatial-intelligence-data-factory/output/line_runs/tc06_failure_replay_2026-02-15_210327_583381.json`

## Rule Fix Suggestions
- R-001 清洗阶段兜底输出: 当 cleaning 产物为空时，回退到 normalize(raw_address) 作为最小可用输出，避免直接 CLEANING_INVALID_OUTPUT。 (risk: 可能引入低质量候选，需结合质量阈值过滤。)
- R-002 清洗失败分类细化: 将 CLEANING_INVALID_OUTPUT 拆分为 EMPTY_AFTER_CLEAN / INVALID_CHARSET / COMPONENT_MISSING，便于针对性修复。 (risk: 错误码枚举变更需同步观测与告警规则。)
- R-003 样本准入预检查: 在 parse 前增加地址长度、数字门牌、行政区命中预检查；不满足则标记可回放失败并保留结构化原因。 (risk: 过严规则可能误拒真实地址。)
