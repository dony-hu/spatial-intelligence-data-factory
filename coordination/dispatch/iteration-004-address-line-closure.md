# Iteration-004 派单：dispatch-address-line-closure-002

- 任务下发时间（本地）：2026-02-15 20:58:53 CST
- 总目标：24小时内完成地址治理产线“对外可演示 GO”收敛

## 收敛优先级（按影响力）

1. 修复 NO_GO 根因并重跑 gate（web_e2e optimize timeout）。
2. 将 `wp-address-topology-v1.0.1` 与 `wp-address-topology-v1.0.2` 推到可验收状态回写一致。
3. 完成看板任务详情数据源切换，确保“任务下发时间/任务提示词”展示最新落盘。
4. 固化管理层演示包：成功样本、失败+回放样本、观测截图、Go/No-Go 单。

## 各线任务包

### 项目管理总控线
- 工作包：`wp-address-topology-v1.0.1`, `wp-address-topology-v1.0.2`, `wp-pm-dashboard-test-progress-v0.1.0`, `wp-test-panel-sql-query-readonly-v0.1.0`
- 目标：跨线收口与最终决策。
- 必交：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。

### 工程监理线
- 工作包：`wp-address-topology-v1.0.1`, `wp-address-topology-v1.0.2`, `wp-pm-dashboard-test-progress-v0.1.0`, `wp-test-panel-sql-query-readonly-v0.1.0`
- 目标：检查全线无越界、无抄近路、无职责串改。
- 必交：合规巡检报告（越界审查 / mock 审查 / 测试与研发边界审查 / 看板边界审查）与处置建议。
- 边界：工程监理线仅输出项目级监理审计报告，不修改任何项目中的工作输出。

### 核心引擎与运行时线
- 工作包：`wp-core-engine-governance-api-lab-p0-v0.1.0`, `wp-test-panel-sql-query-readonly-v0.1.0`
- 目标：修复 `optimize` 超时路径，重跑 web_e2e，保持 P0 gate=GO。
- 必交：超时修复说明、回归结果、风险披露。

### 产线执行与回传闭环线
- 工作包：`wp-address-topology-v1.0.1`, `wp-address-topology-v1.0.2`
- 目标：产出“当次新鲜”成功/失败/回放证据链（非历史复用）。
- 必交：Run Report / Replay Report / line_feedback 回传文件与 hash。

### 地址算法与治理规则线
- 工作包：`wp-address-topology-v1.0.1`, `wp-address-topology-v1.0.2`
- 目标：稳定样本命中率，固定演示输入输出口径。
- 必交：10条样本统计、失败样本原因分布、修正建议。

### 可观测与运营指标线
- 工作包：`wp-address-topology-v1.0.2`, `wp-pm-dashboard-test-progress-v0.1.0`
- 目标：观测页可直接看到状态/质量分/回放引用。
- 必交：观测截图（含时间）、字段映射说明、查询路径。

### 测试平台与质量门槛线
- 工作包：`wp-pm-dashboard-test-progress-v0.1.0`, `wp-test-panel-sql-query-readonly-v0.1.0`
- 目标：web_e2e 全量重跑，SQL 只读能力完成安全回归。
- 必交：测试报告、门槛判定、失败定位与复测计划。

### 可信数据Hub线
- 工作包：`wp-core-engine-trust-data-hub-p0-v0.1.0`
- 目标：为演示链路提供可信证据映射与回放引用。
- 必交：source/snapshot 样例、接口清单、联调结果。
