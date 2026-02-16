# Iteration-005 在制任务清单（执行优先级）

- 日期：2026-02-15
- 来源：`coordination/status/overview.md`、`coordination/status/pm-dashboard.md`、`output/dashboard/dashboard_events.jsonl`
- 目标：把当前未完事项转为可执行待办，避免口径漂移。

## P0（必须先完成）

1. 修复夜间门槛失败并恢复统一发布口径
- 问题：`suite_web_e2e_catalog` 夜间失败导致 `release_decision_changed=NO_GO`
- 验收：夜间回归恢复 `passed`，并在总控与看板状态同步为一致结论
- 证据：`output/workpackages/nightly-quality-gate-*.md`、`output/dashboard/dashboard_events.jsonl`

2. 完成 Iteration-005 看板合并任务包
- 范围：工程监理可视化 + 项目介绍双层结构 + 四卡片 + sticky + 密度切换
- 验收：`coordination/dispatch/iteration-005-dashboard-next-round-merged.md` 验收项全勾选
- 证据：`web/dashboard/*` 改动、截图、自测记录

3. 管理看板线状态回写与门禁对齐
- 要求：状态文件中的 `进度/Blocker/ETA` 与门槛结果一致，不再出现“状态完成但门槛 NO_GO”
- 证据：`coordination/status/pm-dashboard.md`、`coordination/status/overview.md`

## P1（P0 后推进）

1. 工程监理线首轮审计报告落地
- 验收：形成审计结论与越界检查清单
- 证据：工程监理线状态文件与审计报告路径

2. 技能编排字段在后续派单全面落地
- 要求：新增派单全部包含 `skill_profile/skill_entry/skill_exit_gate`
- 证据：`coordination/dispatch/*.md`

3. 事件流与状态自动一致性检查
- 目标：减少人工漏回写，避免总控口径滞后
- 证据：新增脚本或检查流程文档

## 当前建议执行顺序

1) 先处理夜间 `NO_GO`（P0-1）
2) 并行推进看板任务包开发（P0-2）
3) 完成状态回写一致性收口（P0-3）
4) 再推进 P1 审计与自动化增强
