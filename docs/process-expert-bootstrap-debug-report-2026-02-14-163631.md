# Process Expert 自举调试报告（地址用例驱动）

## 1) 目标与范围

- 目标：验证 Agent 在真实 LLM 模式下，基于现有地址用例进行多轮工艺文档与工具脚本迭代，并完整记录每轮交互与产出。
- 用例集：`testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json`（15 条）。
- 运行模式：真实 LLM（无 mock）。

## 2) 执行参数

- 命令：

```bash
/Users/huda/Code/.venv/bin/python scripts/run_process_expert_bootstrap.py \
  --cases-file testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json \
  --output-dir output/process_expert_bootstrap \
  --max-rounds 3 \
  --min-rounds 3 \
  --score-threshold 0.99
```

- 运行 ID：`bootstrap_20260214_163631`
- 输出目录：`output/process_expert_bootstrap/bootstrap_20260214_163631`

## 3) 轮次结果概览

| Round | Stage  | Score | Tool Count | Draft ID         | 结论 |
|------:|--------|------:|-----------:|------------------|------|
| 1     | design | 1.0   | 3          | draft_a6a64b0d80 | 通过 |
| 2     | modify | 1.0   | 4          | draft_a26804d210 | 通过 |
| 3     | modify | 1.0   | 4          | draft_b651e12bb0 | 通过 |

补充：
- `llm_interaction_count = 5`
- `meets_threshold = true`

## 4) LLM 多轮交互可追踪性

已输出逐事件交互记录，包含：
- `generate_plan`：输入 requirement、发送给 LLM 的 prompt、LLM 原始回答、归一化 plan；
- `suggest_change_request`：输入 audit 与 process_code、prompt、LLM 原始回答、最终 change_request。

交互原文文件：
- `output/process_expert_bootstrap/bootstrap_20260214_163631/llm_interactions.json`
- `output/process_expert_bootstrap/bootstrap_20260214_163631/llm_interactions.jsonl`

## 5) 轮次产物位置

- Round 1:
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_01_design/process_doc.md`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_01_design/tool_scripts/`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_01_design/audit.json`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_01_design/result.json`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_01_design/llm_trace.json`

- Round 2:
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_02_modify/process_doc.md`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_02_modify/tool_scripts/`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_02_modify/audit.json`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_02_modify/result.json`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_02_modify/llm_trace.json`

- Round 3:
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_03_modify/process_doc.md`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_03_modify/tool_scripts/`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_03_modify/audit.json`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_03_modify/result.json`
  - `output/process_expert_bootstrap/bootstrap_20260214_163631/round_03_modify/llm_trace.json`

## 6) 原始日志（原文）

- 终端原始日志：`output/process_expert_bootstrap/bootstrap_debug_20260214_163631.log`
- 原始日志合集（终端 + LLM JSONL）：`output/process_expert_bootstrap/bootstrap_20260214_163631/raw_log_bundle.txt`

## 7) 本轮结论

- 已实现“地址用例驱动 + 真实 LLM + 多轮迭代 + 逐轮交互可追踪”。
- 当前审计分数持续满分（1.0），说明现有审计规则对“是否需要继续优化”的区分度偏低。
- 下一步建议：对审计项引入更强约束（例如脚本语义覆盖率、变更有效性、与用例失败模式的显式映射）以驱动真正有增益的迭代。
