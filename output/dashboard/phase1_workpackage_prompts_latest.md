# Phase 1 工作包提示词（最新）

- 批次：dispatch-phase1-pg-foundation-002
- 任务下发时间（本地）：2026-02-16 11:22:20 CST
- 目标：PG统一架构落地（可运行 + 可观测 + 可追踪）

## 全局要求

1. 数据库权威源统一为 Postgres。
2. `line_feedback_contract` 使用 `pg://...` 引用并固定字段。
3. `trace_id/agent_run_id` 全链路透传可追溯。
4. 每条线必须回写状态、证据与发布决策。

## 各线可复制提示词

1. 项目管理总控线（发给：项目管理总控线-Codex）
`你是该工作线执行负责人。工作线：项目管理总控线。负责人：项目管理总控线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-orchestrator-phase1-crossline-closure-v1.0.0。下发提示词：你负责本轮总控收敛与发布决策。必须完成：1) 汇总10条线Done/Next/Blocker/ETA/证据；2) 校验Phase1发布门槛；3) 输出管理层验收包与Go/No-Go单。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

2. 数据库专家（发给：数据库专家-Codex）
`你是该工作线执行负责人。工作线：数据库专家。负责人：数据库专家-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-db-pg-canonical-model-v1.0.0。下发提示词：你负责PG统一模型冻结。必须完成：1) addr主链路DDL与约束；2) 迁移/回滚脚本；3) address_line语义层视图与回归SQL。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

3. 工程监理线（发给：工程监理线-Codex）
`你是该工作线执行负责人。工作线：工程监理线。负责人：工程监理线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-engineering-supervisor-phase1-audit-v1.0.0。下发提示词：你负责独立监理审计。必须完成：1) 越界改动检查；2) mock抄近路检查；3) 测试与研发边界检查；4) 发布建议。仅输出报告不改代码。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

4. 核心引擎与运行时线（发给：核心引擎与运行时线-Codex）
`你是该工作线执行负责人。工作线：核心引擎与运行时线。负责人：核心引擎与运行时线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-runtime-pg-repository-switch-v1.0.0。下发提示词：你负责运行时PG主读写切换。必须完成：1) 仓储层PG为准；2) api_audit_log落库；3) agent_execution_log落库；4) 回归验证。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

5. 产线执行与回传闭环线（发给：产线执行与回传闭环线-Codex）
`你是该工作线执行负责人。工作线：产线执行与回传闭环线。负责人：产线执行与回传闭环线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-line-feedback-contract-pg-v1.0.0。下发提示词：你负责回传合约PG化。必须完成：1) line_feedback_contract固定字段；2) failure/replay PG引用；3) CI阻断校验。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

6. 可信数据Hub线（发给：可信数据Hub线-Codex）
`你是该工作线执行负责人。工作线：可信数据Hub线。负责人：可信数据Hub线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-trust-evidence-index-phase1-v1.0.0。下发提示词：你负责trust证据索引Phase1。必须完成：1) 证据字典与schema_version；2) 映射规则；3) 查询键与验收SQL包；4) GO/NO_GO建议。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

7. 地址算法与治理规则线（发给：地址算法与治理规则线-Codex）
`你是该工作线执行负责人。工作线：地址算法与治理规则线。负责人：地址算法与治理规则线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-address-canonical-pg-baseline-v1.0.0。下发提示词：你负责地址标准化质量基线。必须完成：1) addr_canonical字段质量报告；2) 低置信度分布；3) 失败分类与改进建议。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

8. 测试平台与质量门槛线（发给：测试平台与质量门槛线-Codex）
`你是该工作线执行负责人。工作线：测试平台与质量门槛线。负责人：测试平台与质量门槛线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-pg-only-integration-baseline-v1.0.0。下发提示词：你负责PG-only发布硬门。必须完成：1) 集成测试；2) SQLite回落检测；3) 门槛判定单；4) 失败分类。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

9. 可观测与运营指标线（发给：可观测与运营指标线-Codex）
`你是该工作线执行负责人。工作线：可观测与运营指标线。负责人：可观测与运营指标线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-observability-phase1-run-test-sql-map-v1.0.0。下发提示词：你负责可观测补全。必须完成：1) 测试结果映射；2) 执行过程映射；3) SQL交互映射；4) 缺口补齐计划。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`

10. 管理看板研发线（发给：管理看板研发线-Codex）
`你是该工作线执行负责人。工作线：管理看板研发线。负责人：管理看板研发线-Codex。任务批次ID：dispatch-phase1-pg-foundation-002。任务下发时间（本地）：2026-02-16 11:22:20 CST。任务工作包：wp-dashboard-phase1-structured-rollup-v1.0.0。下发提示词：你负责管理看板结构化展示。必须完成：1) 管理摘要+展开详情双层；2) 缺字段标黄；3) 测试进展可视化与跳转。 回传格式：Package Status Matrix / Top Risks / Go-NoGo Decision / Rollback Plan / Next 48h Plan。执行要求：以可验证产出+可追溯证据+风险前置披露为标准推进，并在完成后同步状态回写。`
