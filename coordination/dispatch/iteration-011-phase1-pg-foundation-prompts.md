# Iteration-011 派单：Phase 1（PG基础切换）工作包提示词

- 下发时间（本地）：2026-02-16 10:10:00 CST
- Phase：Phase 1 - PG基础切换（单一事实源）
- 总目标：完成从 SQLite/内存混合态到 PG 主数据源切换，形成可验收的最小闭环
- 总控约束：禁止回落 SQLite 作为权威数据源；内存仅缓存；所有回写必须有证据链接

## 全局完成标准（DoD）

1. 核心链路读写以 PG 为准（任务、标准化结果、回放、审计）。
2. `line_feedback_contract` 引用规范切到 `pg://...`。
3. 发布门禁中出现 SQLite 权威依赖即 `NO_GO`。
4. 每条线提交状态回写文件（本地时间 + 证据路径 + Go/No-Go）。

## 1) 数据库专家

你是该工作线执行负责人，请按以下任务提示推进：
工作线：数据库专家
负责人：数据库专家-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-db-pg-canonical-model-v1.0.0
下发提示词：你负责PG数据模型冻结。必须完成：1) 核心表结构与约束（非空/枚举/FK）；2) 迁移脚本；3) `address_line` 兼容视图；4) 回归SQL检查脚本。回传格式：Done / Next / Blocker / ETA（本地时间） / DB Model Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：输出 schema 版本号、DDL 变更清单、迁移回滚策略、数据质量检查结果。

## 2) 工程监理线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：工程监理线
负责人：工程监理-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-engineering-supervisor-phase1-audit-v1.0.0
下发提示词：你负责Phase1合规审计。必须完成：1) 检查是否存在SQLite权威依赖；2) 检查是否出现越界改动；3) 输出P0/P1问题清单与Hold建议。回传格式：Compliance Check Matrix / Violations / Risk Level / Rectification Actions / Hold-or-Release Recommendation。
执行要求：仅输出审计报告，不修改项目工作输出。

## 3) 核心引擎与运行时线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：核心引擎与运行时线
负责人：核心引擎与运行时线-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-runtime-pg-repository-switch-v1.0.0
下发提示词：你负责仓储层切换。必须完成：1) PG主读写、内存缓存化；2) API中间件统一审计落库；3) 执行器统一写 `agent_execution_log`。回传格式：Done / Next / Blocker / ETA（本地时间） / Runtime Switch Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：标注受影响仓储与路由清单，附回归测试证据。

## 4) 产线执行与回传闭环线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：产线执行与回传闭环线
负责人：产线执行与回传闭环线-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-line-feedback-contract-pg-v1.0.0
下发提示词：你负责回传合约PG化。必须完成：1) `line_feedback_contract` 引用改为 `pg://address_line.failure_queue` / `pg://address_line.replay_runs`；2) 回放链路改为PG读写；3) 生成当次新鲜证据。回传格式：Done / Next / Blocker / ETA（本地时间） / Contract Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：保留失败/回放样本与引用一致性校验结果。

## 5) 可信数据Hub线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：可信数据Hub线
负责人：可信数据Hub线-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-trust-evidence-index-phase1-v1.0.0
下发提示词：你负责证据索引对齐。必须完成：1) evidence/source/snapshot/replay 字段字典；2) 关联任务与批次映射；3) 数据字典版本声明。回传格式：Done / Next / Blocker / ETA（本地时间） / Evidence Index Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：给出可查询键与示例查询。

## 6) 地址算法与治理规则线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：地址算法与治理规则线
负责人：地址算法与治理规则线-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-address-canonical-pg-baseline-v1.0.0
下发提示词：你负责标准化字段沉淀基线。必须完成：1) `addr_canonical` 字段完整性；2) 置信度与策略口径；3) 10条样本质量基线。回传格式：Done / Next / Blocker / ETA（本地时间） / Canonical Baseline Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：输出低置信度分布和失败分类。

## 7) 测试平台与质量门槛线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：测试平台与质量门槛线
负责人：测试平台与质量门槛线-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-pg-only-integration-baseline-v1.0.0
下发提示词：你负责Phase1硬门。必须完成：1) PG-only 集成测试；2) SQLite回落检测；3) 关键门槛判定回写。回传格式：Done / Next / Blocker / ETA（本地时间） / Test Gate Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：失败需给出 failure_type/severity/retryable/gate_impact。

## 8) 可观测与运营指标线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：可观测与运营指标线
负责人：可观测与运营指标线-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-observability-phase1-run-test-sql-map-v1.0.0
下发提示词：你负责Phase1指标映射。必须完成：1) 测试结果视图字段；2) 执行过程时间线字段；3) 只读SQL查询能力映射与告警字段。回传格式：Done / Next / Blocker / ETA（本地时间） / Observability Mapping Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：提交“管理层可读字段表”与缺失字段补齐计划。

## 9) 管理看板研发线

你是该工作线执行负责人，请按以下任务提示推进：
工作线：管理看板研发线
负责人：管理看板研发线-Codex
任务批次ID：dispatch-phase1-pg-foundation-001
任务下发时间（本地）：2026-02-16 10:10:00 CST
任务工作包：wp-dashboard-phase1-structured-rollup-v1.0.0
下发提示词：你负责Phase1结构化展示。必须完成：1) 读取Phase1结构化状态回写；2) 展示包级/线级/项目级三层门槛；3) 缺ETA或证据标黄。回传格式：Done / Next / Blocker / ETA（本地时间） / Dashboard Integration Report / Evidence / Release Decision（GO|NO_GO）。
执行要求：不改生产业务逻辑，只改看板展示与数据读取。
