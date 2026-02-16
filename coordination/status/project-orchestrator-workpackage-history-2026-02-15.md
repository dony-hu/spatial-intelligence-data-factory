# 项目管理总控线历史工作包总账（接任基线）

- 生成时间：2026-02-15
- 角色：项目管理总控线（接任）
- 数据来源：`output/dashboard/workpackages_live.json`、`output/dashboard/dashboard_events.jsonl`、`coordination/status/project-orchestrator.md`

## 1. 历史工作包盘点（截至当前）

| workpackage_id | 优先级 | owner_line | 状态 | release_decision | 备注 |
|---|---|---|---|---|---|
| wp-core-engine-p0-stabilization-v0.1.0 | P0 | 核心引擎与运行时线 | done | NO_GO | 夜间门槛事件触发回退口径 |
| wp-core-engine-address-core-p0-v0.1.0 | P0 | 地址算法与治理规则线 | done | GO | 已验收 |
| wp-core-engine-governance-api-lab-p0-v0.1.0 | P0 | 核心引擎与运行时线 | done | GO | 已验收 |
| wp-core-engine-trust-data-hub-p0-v0.1.0 | P0 | 可信数据Hub线 | done | GO | 已验收 |
| wp-address-topology-v1.0.1 | P1 | 产线执行与回传闭环线 | done | GO | 已验收 |
| wp-address-topology-v1.0.2 | P1 | 产线执行与回传闭环线 | done | GO | 已验收 |
| wp-pm-dashboard-test-progress-v0.1.0 | P2 | 项目管理总控线 | done | GO（历史）/NO_GO（夜间） | 日间收口后夜间回归失败 |
| wp-test-panel-sql-query-readonly-v0.1.0 | P2 | 测试平台与质量门槛线 | done | GO | 夜间回归继续通过 |

## 2. 历史派单批次结论

1. `dispatch-address-line-closure-001`：完成基础收敛与证据链搭建。
2. `dispatch-address-line-closure-002`：四目标包收口，形成历史 `GO` 决策。
3. Iteration-005（在制）：管理看板合并任务包已下发，尚未验收关闭。

## 3. 当前真实风险（接任后优先处理）

1. 质量门槛口径冲突：
- 日间管理结论存在 `GO`，但夜间事件已回写 `NO_GO`（`suite_web_e2e_catalog` 失败）。
2. 总控状态与执行状态同步滞后：
- 部分状态文件未完整反映夜间门槛结果与 Iteration-005 在制事实。
3. 新派单尚未闭环：
- Iteration-005 验收项未完成，仍需工程与测试联动收口。

## 4. 接任后的执行原则

- 以事件流门槛为准：`dashboard_events.jsonl` 最新 `release_decision_changed` 优先于历史静态结论。
- 以 `GO/NO_GO` 一致性为准：总控、工作线、看板三个视图保持同一口径。
- 以证据链为准：无测试证据、无门槛结果、无回写事件，不得判定完成。

## 5. 接任后第一批动作（P0）

1. 推进夜间 web_e2e 修复与复跑，恢复 `GO`。
2. 跟进 Iteration-005 合并任务包实现与验收。
3. 同步状态文件与事件流，消除“完成但 NO_GO”冲突。
