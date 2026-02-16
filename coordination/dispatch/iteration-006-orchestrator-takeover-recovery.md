# Iteration-006 派单：项目管理总控线接任恢复包

- 下发时间（本地）：2026-02-15 22:20:00 CST
- 工作线：项目管理总控线
- 负责人：项目管理总控线-Codex（接任）
- 目标：完成“夜间 NO_GO 恢复 + Iteration-005 收口 + 总控口径一致化”

## 研发治理字段（强制）

- workline: 项目管理总控线
- A_role: 平台PM
- R_owner: 项目管理总控线负责人（Codex）
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.tasks
- skill_exit_gate: checklist_pass
- go_no_go_gate:
  - `suite_web_e2e_catalog` 夜间回归恢复 `passed`
  - Iteration-005 验收项全部完成并证据齐全
  - 总控视图、子线状态、事件流三者口径一致
- evidence_paths:
  - output/workpackages/nightly-quality-gate-*.md
  - coordination/status/overview.md
  - coordination/status/pm-dashboard.md
  - coordination/status/project-orchestrator.md
  - output/dashboard/dashboard_events.jsonl

## 子任务拆解

### T1 夜间门槛恢复（P0）

- 对接测试平台与质量门槛线，修复 `suite_web_e2e_catalog` 失败并完成复跑。
- 回写 `test_synced` 与 `release_decision_changed` 事件。

### T2 Iteration-005 收口（P0）

- 跟进管理看板研发线交付：
  - 工程监理可视化
  - 项目介绍双层结构
  - 四卡片 + sticky + 密度切换
- 按验收单逐项勾选，未满足项不得标记完成。

### T3 总控口径一致化（P0）

- 对齐三层口径：
  1. `coordination/status/*.md`
  2. `output/dashboard/*.json`
  3. `output/dashboard/dashboard_events.jsonl`
- 保证“门槛最新结论优先”。

### T4 工程监理首报接入（P1）

- 收集工程监理线首份审计报告并纳入总控风险区块。

## 验收标准

- [ ] 夜间门槛恢复为 `GO`
- [ ] Iteration-005 验收项全部通过
- [ ] 总控/子线/事件流口径一致
- [ ] 形成恢复说明与证据链
