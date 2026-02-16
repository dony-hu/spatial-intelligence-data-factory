# Iteration-007 派单：全角色下一迭代工作包分配（总控下发）

- 下发时间（本地）：2026-02-15 22:40:00 CST
- 派单角色：项目管理总控线-Codex（接任）
- 批次ID：dispatch-address-line-closure-003
- 总目标：修复夜间门槛 NO_GO、完成看板合并任务包收口、建立跨线一致口径并准备下一次 GO 发布。

## 研发治理口径（统一）

- A_role：平台PM（总控最终负责）
- R_owner：各工作线负责人
- 必填字段：`workline/A_role/R_owner/agent_capabilities/skill_profile/skill_entry/skill_exit_gate/go_no_go_gate/evidence_paths`

## 角色工作包分配（下一迭代）

### 1) 项目管理总控线
- workline: 项目管理总控线
- R_owner: 项目管理总控线-Codex
- workpackage_id: `wp-orchestrator-recovery-v0.1.0`
- 目标: 统一日间/夜间 GO-NO_GO 口径并完成跨线收口决策
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.tasks
- skill_exit_gate: checklist_pass

### 2) 工程监理线
- workline: 工程监理线
- R_owner: 工程监理-Codex
- workpackage_id: `wp-engineering-supervisor-audit-v0.1.0`
- 目标: 输出首份项目级合规审计报告并给出 HOLD/RELEASE 建议
- agent_capabilities: 审计 + 影响分析
- skill_profile: engineering_supervisor_v1
- skill_entry: speckit.analyze
- skill_exit_gate: checklist_pass

### 3) 核心引擎与运行时线
- workline: 核心引擎与运行时线
- R_owner: 核心引擎与运行时线-Codex
- workpackage_id: `wp-core-runtime-nightly-recover-v0.1.0`
- 目标: 修复 `suite_web_e2e_catalog` 夜间失败并恢复 quality gate
- agent_capabilities: 执行 + 编排
- skill_profile: core_runtime_v1
- skill_entry: speckit.plan
- skill_exit_gate: analyze_pass

### 4) 产线执行与回传闭环线
- workline: 产线执行与回传闭环线
- R_owner: 产线执行与回传闭环线-Codex
- workpackage_id: `wp-line-feedback-ci-enforcement-v0.1.0`
- 目标: 将 `line_feedback.latest.sha256` 校验接入 CI 阻断
- agent_capabilities: 执行 + 质量
- skill_profile: line_execution_v1
- skill_entry: speckit.tasks
- skill_exit_gate: analyze_pass

### 5) 可信数据Hub线
- workline: 可信数据Hub线
- R_owner: 可信数据Hub线-Codex
- workpackage_id: `wp-trust-hub-replay-persistence-v0.1.0`
- 目标: 完成 replay 持久化联调并提供证据映射
- agent_capabilities: 建模 + 执行
- skill_profile: trust_data_hub_v1
- skill_entry: speckit.plan
- skill_exit_gate: analyze_pass

### 6) 地址算法与治理规则线
- workline: 地址算法与治理规则线
- R_owner: 地址算法与治理规则线-Codex
- workpackage_id: `wp-address-rules-stability-v0.2.0`
- 目标: 10条样本稳定性提升与失败分类收敛
- agent_capabilities: 数据探索 + 建模 + 质量
- skill_profile: address_rules_v1
- skill_entry: speckit.specify
- skill_exit_gate: analyze_pass

### 7) 测试平台与质量门槛线
- workline: 测试平台与质量门槛线
- R_owner: 测试平台与质量门槛线-Codex
- workpackage_id: `wp-quality-gate-nightly-hardening-v0.1.0`
- 目标: 固化 nightly 失败告警与自动复测机制
- agent_capabilities: 质量 + 审计
- skill_profile: test_quality_gate_v1
- skill_entry: speckit.tasks
- skill_exit_gate: checklist_pass

### 8) 可观测与运营指标线
- workline: 可观测与运营指标线
- R_owner: 可观测与运营指标线-Codex
- workpackage_id: `wp-observability-gate-alignment-v0.1.0`
- 目标: 看板展示口径与门槛结果实时对齐（含 NO_GO 风险提示）
- agent_capabilities: 编排 + 推理服务
- skill_profile: observability_ops_v1
- skill_entry: speckit.plan
- skill_exit_gate: checklist_pass

### 9) 管理看板研发线
- workline: 管理看板研发线
- R_owner: 管理看板研发线-Codex
- workpackage_id: `wp-dashboard-iteration-005-closeout-v0.1.0`
- 目标: 完成四卡片/sticky/密度切换/缺字段标黄并提交验收证据
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.implement
- skill_exit_gate: checklist_pass

## 总体验收门槛（批次）

- [ ] 夜间 `suite_web_e2e_catalog` 恢复 `passed`
- [ ] Iteration-005 验收清单全部通过
- [ ] 工程监理线首份合规报告发布
- [ ] 总控/工作线/看板口径一致（事件流可追溯）
