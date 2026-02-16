# 管理层演示路径说明：地址治理产线可观测（2026-02-15）

## 演示入口
- 观测页：`http://127.0.0.1:8000/v1/governance/lab/observability/view?env=prod`
- 快照接口：`http://127.0.0.1:8000/v1/governance/lab/observability/snapshot?env=prod`

## 演示步骤
1. 打开观测页，确认顶部 `最后刷新` 时间（用于证明时效性）。
2. 查看区块 `地址治理产线最小指标`：
   - 任务状态：`address_line.task_status`
   - 质量分：`address_line.quality_score`
3. 查看区块 `失败回放引用`：
   - 点击 `ref` 进入回放/失败明细入口。
4. 查看区块 `样本到观测记录关联`：
   - 选择任一 `case_id`。
   - 点击 `observability_ref` 跳转到 `/v1/governance/lab/coverage/view?case_id={case_id}`。
   - 完成“样本 -> 观测记录”的可追踪演示。

## 证据链文件
- 截图（含时间）：`output/observability/address_line_observability_demo_20260215_201023.png`
- 样本追踪快照：`output/observability/address_line_sample_trace_20260215_201023.json`
- 字段说明：`docs/address-line-observability-fields-2026-02-15.md`

