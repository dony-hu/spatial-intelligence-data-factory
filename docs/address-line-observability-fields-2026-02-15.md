# 地址治理产线可观测字段说明（最小接入）

更新时间（UTC）：2026-02-15
接口基线：`/v1/governance/lab/observability/snapshot`

## 字段清单（字段名 + 含义 + 来源）

| 字段名 | 含义 | 来源 |
| --- | --- | --- |
| `address_line.task_status` | 地址治理产线任务状态分布（如 `PENDING`/`SUCCEEDED`/`FAILED`/`REVIEWED`） | `REPOSITORY.get_ops_summary().status_counts`（内存任务态 + 任务执行状态） |
| `address_line.quality_score` | 地址治理产线质量分（0-100），当前按平均置信度线性换算：`avg_confidence * 100` | `REPOSITORY.get_ops_summary().avg_confidence` |
| `address_line.failure_replay_refs[].type` | 失败回放引用类型（任务失败或覆盖集失败） | 后端聚合逻辑 `_address_line_metrics()` |
| `address_line.failure_replay_refs[].ref` | 失败回放入口链接（可用于管理层下钻） | 任务失败：`/v1/governance/tasks/{task_id}`；覆盖失败：`/v1/governance/lab/coverage/view?result=fail...` |
| `address_line.failure_replay_refs[].note` | 回放引用补充说明（如失败条数、报告文件） | 任务状态 + 覆盖报告 `output/lab_mode/cn1300_module_coverage_*.json` |
| `address_line.sample_trace_links[].case_id` | 产线样本 ID，可用于管理层点选具体样本 | 最新覆盖报告 `case_details[].case_id` |
| `address_line.sample_trace_links[].raw_text` | 样本原文地址 | 最新覆盖报告 `case_details[].raw_text` |
| `address_line.sample_trace_links[].overall_result` | 样本结果（pass/fail） | 最新覆盖报告 `case_details[].overall_result` |
| `address_line.sample_trace_links[].observability_ref` | 从样本下钻到观测记录的页面链接 | `/v1/governance/lab/coverage/view?case_id={case_id}` |

## 页面呈现位置

页面：`/v1/governance/lab/observability/view`

- 区块 `地址治理产线最小指标`：展示 `task_status` 与 `quality_score`
- 区块 `失败回放引用`：展示 `failure_replay_refs`
- 区块 `样本到观测记录关联`：展示 `sample_trace_links`

## 样本追踪路径

1. 打开 `/v1/governance/lab/observability/view`
2. 在 `样本到观测记录关联` 区块选择 `case_id`
3. 点击 `observability_ref`
4. 跳转 `/v1/governance/lab/coverage/view?case_id={case_id}` 查看对应观测记录
