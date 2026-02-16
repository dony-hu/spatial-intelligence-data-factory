# Iteration-008 派单：BM Master 下一迭代任务包（总控下发）

- 下发时间（本地）：2026-02-15 23:10:00 CST
- 派单角色：项目管理总控线-Codex（BM Master）
- 批次ID：dispatch-address-line-closure-004
- 总目标：以“夜间门槛优先”恢复质量红线，完成口径统一并形成可签发 GO 候选。

## 研发治理口径（统一）

- A_role：平台PM（总控最终负责）
- R_owner：各工作线负责人
- 必填字段：`workline/A_role/R_owner/agent_capabilities/skill_profile/skill_entry/skill_exit_gate/go_no_go_gate/evidence_paths`

## 角色任务包分配（下一迭代）

### 1) 项目管理总控线
- workline: 项目管理总控线
- R_owner: 项目管理总控线-Codex
- workpackage_id: `wp-orchestrator-decision-unification-v0.2.0`
- 目标: 统一日间/夜间门槛口径并输出唯一发布决策单
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.tasks
- skill_exit_gate: checklist_pass

### 2) 工程监理线
- workline: 工程监理线
- R_owner: 工程监理-Codex
- workpackage_id: `wp-engineering-supervisor-audit-v0.2.0`
- 目标: 发布首份项目级监理审计报告（越界/抄近路/HOLD-RELEASE）
- agent_capabilities: 审计 + 影响分析
- skill_profile: engineering_supervisor_v1
- skill_entry: speckit.analyze
- skill_exit_gate: checklist_pass

### 3) 核心引擎与运行时线
- workline: 核心引擎与运行时线
- R_owner: 核心引擎与运行时线-Codex
- workpackage_id: `wp-core-runtime-web-e2e-recovery-v0.2.0`
- 目标: 修复 `suite_web_e2e_catalog` 并实现夜间连续两次 `passed`
- agent_capabilities: 执行 + 编排
- skill_profile: core_runtime_v1
- skill_entry: speckit.plan
- skill_exit_gate: analyze_pass

### 4) 产线执行与回传闭环线
- workline: 产线执行与回传闭环线
- R_owner: 产线执行与回传闭环线-Codex
- workpackage_id: `wp-line-feedback-ci-enforcement-v0.2.0`
- 目标: `line_feedback.latest.sha256` 校验接入 CI 强阻断并完成演示
- agent_capabilities: 执行 + 质量
- skill_profile: line_execution_v1
- skill_entry: speckit.tasks
- skill_exit_gate: analyze_pass

### 5) 可信数据Hub线
- workline: 可信数据Hub线
- R_owner: 可信数据Hub线-Codex
- workpackage_id: `wp-trust-hub-replay-persistence-v0.2.0`
- 目标: 完成 replay 持久化联调并补齐证据映射一致性
- agent_capabilities: 建模 + 执行
- skill_profile: trust_data_hub_v1
- skill_entry: speckit.plan
- skill_exit_gate: analyze_pass

### 6) 地址算法与治理规则线
- workline: 地址算法与治理规则线
- R_owner: 地址算法与治理规则线-Codex
- workpackage_id: `wp-address-rules-stability-v0.3.0`
- 目标: 10条样本稳定性复盘（通过率、失败分类、规则修订）
- agent_capabilities: 数据探索 + 建模 + 质量
- skill_profile: address_rules_v1
- skill_entry: speckit.specify
- skill_exit_gate: analyze_pass

### 7) 测试平台与质量门槛线
- workline: 测试平台与质量门槛线
- R_owner: 测试平台与质量门槛线-Codex
- workpackage_id: `wp-quality-gate-nightly-hardening-v0.2.0`
- 目标: 建立失败自动复测+失败分型并固化门槛判定模板
- agent_capabilities: 质量 + 审计
- skill_profile: test_quality_gate_v1
- skill_entry: speckit.tasks
- skill_exit_gate: checklist_pass

### 8) 可观测与运营指标线
- workline: 可观测与运营指标线
- R_owner: 可观测与运营指标线-Codex
- workpackage_id: `wp-observability-gate-alignment-v0.2.0`
- 目标: 门槛结果实时映射看板并强化 NO_GO 风险提示
- agent_capabilities: 编排 + 推理服务
- skill_profile: observability_ops_v1
- skill_entry: speckit.plan
- skill_exit_gate: checklist_pass

### 9) 管理看板研发线
- workline: 管理看板研发线
- R_owner: 管理看板研发线-Codex
- workpackage_id: `wp-dashboard-iteration-005-closeout-v0.2.0`
- 目标: 完成 Iteration-005 遗留验收项并提交截图+自测证据
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.implement
- skill_exit_gate: checklist_pass

## 批次验收门槛（dispatch-004）

- [ ] 夜间 `suite_web_e2e_catalog` 连续两次 `passed`
- [ ] 工程监理线首份审计报告发布
- [ ] 看板主视图与事件流门槛状态一致
- [ ] 总控签发唯一 `GO/NO_GO` 决策
