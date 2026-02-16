# 系统可观测字段说明与演示路径（2026-02-16）

## 一、最小指标字段说明（字段名 + 含义 + 来源）

| 字段名 | 含义 | 来源 |
|---|---|---|
| `status`（执行过程行） | 地址治理任务当前状态（如 in_progress/done/blocked） | `output/dashboard/workpackages_live.json` -> `packages[].status` |
| `quality_score`（质量分） | 质量分（0-100），用于管理层快速判断质量水位 | `output/dashboard/test_status_board.json` 的通过率/质量门槛结果映射（看板侧按规则展示） |
| `failure_replay_ref`（失败回放引用） | 失败记录可回放/追溯的引用（失败ID、回放ID或证据链接） | `failure_queue` + `replay_runs`（SQL只读接口）以及 `evidence_ref` |

说明：
- 页面“测试结果视图”中的 `gate_decision` 作为质量门槛结论（GO/NO_GO）。
- 页面“失败分类”与 SQL 面板共同支撑失败回放引用定位。

## 二、样本与观测记录关联

样本追溯链路：
1. 从产线样本（工作包/任务批次）进入执行过程表，定位 `task_batch_id/workpackage_id`。
2. 通过该行 `evidence_ref` 打开对应测试报告或数据文件。
3. 在 SQL 面板执行模板查询：
   - `failure_queue_latest` 获取 `failure_id/status/created_at/payload_json`
   - `replay_runs_latest` 获取 `replay_id/failure_id/status/created_at`
4. 用 `failure_id` 将失败记录与回放记录关联，完成“样本 -> 观测记录 -> 回放引用”闭环。

## 三、管理层演示路径

1. 打开 `/v1/governance/lab/observability/view`。
2. 首页先看摘要：测试结果 + 执行过程（含 Owner/ETA/证据）。
3. 点击“测试结果视图”：确认总览、三层门槛、失败分类。
4. 点击“执行过程视图”：确认链路、关键字段、最近事件时间线（倒序>=20条）。
5. 点击“一键进入 SQL 交互查询”：执行只读模板并展示结果表。
6. 用 `failure_id` 追到 `replay_runs`，展示失败回放引用可查。

## 四、证据索引

- 截图（主看板）：`output/observability/system_observability_management_main_20260216_101612.png`
- 截图（SQL面板）：`output/observability/system_observability_management_sql_20260216_101612.png`
- 管理看板说明：`coordination/status/system-observability-management-dashboard-2026-02-16.md`
- SQL能力说明：`coordination/status/system-observability-sql-capability-2026-02-16.md`
- 自测记录：`output/observability/system_observability_selftest_20260216.json`

