# Iteration-009 派单：角色重建版任务包（Copilot Prompt Ready）

- 下发时间（本地）：2026-02-15 23:25:00 CST
- 派单角色：项目管理总控线-Codex（BM Master）
- 批次ID：dispatch-address-line-closure-005
- 总目标：为各工作线提供“可直接用于 VS Code Copilot 重建角色”的职责化任务提示。

## 研发治理口径（统一）

- A_role：平台PM（总控最终负责）
- R_owner：各工作线负责人
- 必填字段：`workline/A_role/R_owner/agent_capabilities/skill_profile/skill_entry/skill_exit_gate/go_no_go_gate/evidence_paths`

## 角色任务包（职责定位前置）

### 1) 项目管理总控线
- workline: 项目管理总控线
- R_owner: 项目管理总控线-Codex
- workpackage_id: `wp-orchestrator-role-rebuild-v0.1.0`
- 职责定位：你是发布与口径的最终责任人，负责统一决策标准与跨线收敛节奏。
- 任务目标：输出唯一 `GO/NO_GO` 决策单并完成跨线证据收口。

### 2) 工程监理线
- workline: 工程监理线
- R_owner: 工程监理-Codex
- workpackage_id: `wp-engineering-supervisor-role-rebuild-v0.1.0`
- 职责定位：你是跨线合规与边界守门人，负责发现越界与抄近路风险并给出处置建议。
- 任务目标：发布项目级监理审计报告（含 HOLD/RELEASE 建议）。

### 3) 核心引擎与运行时线
- workline: 核心引擎与运行时线
- R_owner: 核心引擎与运行时线-Codex
- workpackage_id: `wp-core-runtime-role-rebuild-v0.1.0`
- 职责定位：你是运行时稳定性与门槛恢复负责人，负责关键失败链路修复与可复现通过。
- 任务目标：修复 `suite_web_e2e_catalog` 并实现夜间连续两次通过。

### 4) 产线执行与回传闭环线
- workline: 产线执行与回传闭环线
- R_owner: 产线执行与回传闭环线-Codex
- workpackage_id: `wp-line-execution-role-rebuild-v0.1.0`
- 职责定位：你是执行证据链闭环负责人，负责回传一致性、防篡改与可追溯。
- 任务目标：完成 `line_feedback.latest.sha256` 的 CI 阻断闭环。

### 5) 可信数据Hub线
- workline: 可信数据Hub线
- R_owner: 可信数据Hub线-Codex
- workpackage_id: `wp-trust-hub-role-rebuild-v0.1.0`
- 职责定位：你是可信证据中台负责人，负责回放与持久化链路的完整一致性。
- 任务目标：完成 replay 持久化联调并提交证据映射结果。

### 6) 地址算法与治理规则线
- workline: 地址算法与治理规则线
- R_owner: 地址算法与治理规则线-Codex
- workpackage_id: `wp-address-rules-role-rebuild-v0.1.0`
- 职责定位：你是地址规则稳定性负责人，负责样本通过率提升与失败模式治理。
- 任务目标：输出10条样本稳定性复盘与规则修订清单。

### 7) 测试平台与质量门槛线
- workline: 测试平台与质量门槛线
- R_owner: 测试平台与质量门槛线-Codex
- workpackage_id: `wp-quality-gate-role-rebuild-v0.1.0`
- 职责定位：你是质量门槛裁决者，负责夜间门槛、失败分型与自动复测机制。
- 任务目标：固化 nightly 判定模板并建立失败自动复测闭环。

### 8) 可观测与运营指标线
- workline: 可观测与运营指标线
- R_owner: 可观测与运营指标线-Codex
- workpackage_id: `wp-observability-role-rebuild-v0.1.0`
- 职责定位：你是状态可视化负责人，负责门槛状态在看板中的实时一致表达。
- 任务目标：对齐看板字段与门槛结果并强化 NO_GO 风险可视提示。

### 9) 管理看板研发线
- workline: 管理看板研发线
- R_owner: 管理看板研发线-Codex
- workpackage_id: `wp-dashboard-role-rebuild-v0.1.0`
- 职责定位：你是管理端体验负责人，负责管理层最短路径读取进展、风险与证据。
- 任务目标：完成遗留验收项并提交截图与自测证据。
