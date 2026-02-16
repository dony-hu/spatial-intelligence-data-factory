# Iteration-011 派单: 下一迭代工作包(总控下发)

- 下发时间(本地): 2026-02-16 09:40:00 CST
- 派单角色: 项目管理总控线-Codex
- 批次ID: dispatch-address-line-closure-007
- 总目标: 修复进度口径不一致, 完成关键技术债设计与验收门槛统一, 形成可签发GO的基础能力.

## 研发治理口径(统一)

- A_role: 平台PM(总控最终负责)
- R_owner: 各工作线负责人
- 必填字段: workline/A_role/R_owner/agent_capabilities/skill_profile/skill_entry/skill_exit_gate/go_no_go_gate/evidence_paths

## 角色工作包分配(下一迭代)

### 1) 项目管理总控线
- workline: 项目管理总控线
- A_role: 平台PM
- R_owner: 项目管理总控线-Codex
- workpackage_id: wp-orchestrator-progress-consistency-v0.1.0
- 目标: 定义"工作线进度=工作包聚合"统一口径, 发布一致性规则与验收清单
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.specify
- skill_exit_gate: checklist_pass
- go_no_go_gate:
  - 进度口径规则文档发布
  - worklines_overview与workpackages_live对齐规则可执行
  - 看板提示字段缺失时有明确提示语
- evidence_paths:
  - coordination/dispatch/iteration-011-next-iteration-workpackages.md
  - output/workpackages/progress-consistency-rule-v0.1.0.md
  - output/dashboard/worklines_overview.json
  - output/dashboard/workpackages_live.json

### 2) 工程监理线
- workline: 工程监理线
- A_role: 平台PM
- R_owner: 工程监理-Codex
- workpackage_id: wp-engineering-supervisor-audit-v0.3.0
- 目标: 对进度口径与数据源一致性执行审计, 输出合规与偏差报告
- agent_capabilities: 审计 + 影响分析
- skill_profile: engineering_supervisor_v1
- skill_entry: speckit.analyze
- skill_exit_gate: checklist_pass
- go_no_go_gate:
  - 审计报告发布
  - 偏差项清单与处置建议齐全
- evidence_paths:
  - output/workpackages/engineering-audit-report-dispatch-007.md
  - output/dashboard/dashboard_events.jsonl

### 3) 核心引擎与运行时线
- workline: 核心引擎与运行时线
- A_role: 平台PM
- R_owner: 核心引擎与运行时线-Codex
- workpackage_id: wp-timeout-policy-unification-v0.1.0
- 目标: 统一超时策略与SLA预算分配, 给出可执行配置清单
- agent_capabilities: 执行 + 编排
- skill_profile: core_runtime_v1
- skill_entry: speckit.plan
- skill_exit_gate: analyze_pass
- go_no_go_gate:
  - 超时预算分配表完成
  - 关键API的超时配置对齐建议完成
- evidence_paths:
  - output/workpackages/timeout-policy-unification-v0.1.0.md
  - services/governance_api/app/models/ops_models.py
  - services/governance_api/app/models/lab_models.py
  - services/trust_data_hub/app/execution/fetchers.py

### 4) 产线执行与回传闭环线
- workline: 产线执行与回传闭环线
- A_role: 平台PM
- R_owner: 产线执行与回传闭环线-Codex
- workpackage_id: wp-line-feedback-schema-v2-v0.1.0
- 目标: 定义line_feedback合约v2 JSON Schema与版本策略(仅设计, 不改代码)
- agent_capabilities: 执行 + 质量
- skill_profile: line_execution_v1
- skill_entry: speckit.specify
- skill_exit_gate: analyze_pass
- go_no_go_gate:
  - schema v2草案完成
  - 兼容性与迁移策略说明完成
- evidence_paths:
  - contracts/line_feedback_contract_v2.schema.json
  - output/workpackages/line-feedback-schema-v2-notes.md

### 5) 可信数据Hub线
- workline: 可信数据Hub线
- A_role: 平台PM
- R_owner: 可信数据Hub线-Codex
- workpackage_id: wp-trust-hub-replay-evidence-index-v0.1.0
- 目标: 设计replay证据索引与持久化映射说明, 输出数据字典
- agent_capabilities: 建模 + 执行
- skill_profile: trust_data_hub_v1
- skill_entry: speckit.plan
- skill_exit_gate: analyze_pass
- go_no_go_gate:
  - 证据索引字段定义完成
  - 映射规则说明完成
- evidence_paths:
  - output/workpackages/trust-hub-replay-evidence-index-v0.1.0.md
  - coordination/status/trust-data-hub.md

### 6) 地址算法与治理规则线
- workline: 地址算法与治理规则线
- A_role: 平台PM
- R_owner: 地址算法与治理规则线-Codex
- workpackage_id: wp-address-rules-stability-v0.4.0
- 目标: 10条样本稳定性复盘, 输出失败分类与修订建议(不改代码)
- agent_capabilities: 数据探索 + 建模 + 质量
- skill_profile: address_rules_v1
- skill_entry: speckit.specify
- skill_exit_gate: analyze_pass
- go_no_go_gate:
  - 失败分类报告完成
  - 修订建议清单完成
- evidence_paths:
  - output/workpackages/address-rules-stability-review-v0.4.0.md
  - testdata/

### 7) 测试平台与质量门槛线
- workline: 测试平台与质量门槛线
- A_role: 平台PM
- R_owner: 测试平台与质量门槛线-Codex
- workpackage_id: wp-quality-gate-rollup-consistency-v0.1.0
- 目标: 定义工作包/工作线门槛对齐规则与一致性回写口径
- agent_capabilities: 质量 + 审计
- skill_profile: test_quality_gate_v1
- skill_entry: speckit.tasks
- skill_exit_gate: checklist_pass
- go_no_go_gate:
  - 门槛对齐规则文档完成
  - 回写字段与事件类型确认
- evidence_paths:
  - output/workpackages/quality-gate-rollup-consistency-v0.1.0.md
  - output/dashboard/test_status_board.json

### 8) 可观测与运营指标线
- workline: 可观测与运营指标线
- A_role: 平台PM
- R_owner: 可观测与运营指标线-Codex
- workpackage_id: wp-observability-metrics-map-v0.1.0
- 目标: 定义跨线指标映射表与缺失指标补齐计划(不改代码)
- agent_capabilities: 编排 + 推理服务
- skill_profile: observability_ops_v1
- skill_entry: speckit.plan
- skill_exit_gate: checklist_pass
- go_no_go_gate:
  - 指标映射表完成
  - 缺失指标与采集计划完成
- evidence_paths:
  - output/workpackages/observability-metrics-map-v0.1.0.md
  - output/dashboard/worklines_overview.json

### 9) 管理看板研发线
- workline: 管理看板研发线
- A_role: 平台PM
- R_owner: 管理看板研发线-Codex
- workpackage_id: wp-dashboard-progress-rollup-v0.1.0
- 目标: 定义进度聚合展示规范与偏差提示规则(不改代码)
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.implement
- skill_exit_gate: checklist_pass
- go_no_go_gate:
  - 进度聚合展示规范完成
  - 偏差提示规则完成
- evidence_paths:
  - output/workpackages/dashboard-progress-rollup-spec-v0.1.0.md
  - web/dashboard/app.js

## 批次验收门槛(dispatch-007)

- [ ] 工作线进度与工作包进度一致性规则发布
- [ ] 进度口径偏差有审计报告
- [ ] 超时策略统一方案完成
- [ ] line_feedback合约v2设计完成
- [ ] 总控输出唯一GO/NO_GO候选决策清单
