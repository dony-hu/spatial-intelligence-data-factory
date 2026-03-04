# PM跨角色统一推进清单（2026-03-02）

## 1. 目标与输入基线

### 1.1 目标

将当前“口径冲突 + P1 积压 + owner 缺失”问题转化为可执行的跨角色推进清单，供 BM Master 汇总后统一派发。

### 1.2 文档基线（已核读）

1. `docs/prd-spatial-intelligence-data-factory-2026-02-28.md`
2. `docs/prd-runtime-observability-dashboard-2026-02-28.md`
3. `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`
4. `docs/architecture-spatial-intelligence-data-factory-2026-02-28.md`
5. `docs/epic-runtime-observability-v2-2026-02-28.md`
6. `docs/epic-pg-only-sqlite-decommission-2026-02-27.md`

### 1.3 当前状态摘要（作为执行入口）

1. 工作包：总 18，done 8，planned 10，GO 7，NO_GO 1，HOLD 10。
2. 测试：suite 5（passed 4 / failed 1），open regression 1。
3. 发布口径冲突：`quality_gates.overall=true` 与 `release_decision=NO_GO` 并存。

## 2. 统一口径（必须先做）

### 2.1 单一发布判定规则（SSOT）

1. 若 `release_gate` 失败，判定 `NO_GO`。
2. 若 `open_regression_count > 0`，判定 `NO_GO`。
3. 仅当以上两项均满足“通过/关闭”时，判定 `GO`。

### 2.2 同步落点（必须同源）

1. `output/dashboard/project_overview.json` 的 `release_decision`
2. `output/dashboard/test_status_board.json` 的 `quality_gates.overall`
3. 工作线总控状态文案（避免“文本GO、门禁NO_GO”）

### 2.3 验收出口

1. 输出“口径一致性核对记录”（Markdown）到 `output/dashboard/`。
2. 在回归关闭记录中附三项证据路径：门禁结果、回归状态、验收报告。

## 3. HOLD工作包推进（10包逐项）

> 推进原则：先“数据与门禁底座”，再“观测与看板”，最后“管理收口签发”。

1. `wp-db-pg-canonical-model-v1.0.0`
- 需要推进：统一多 schema 基线迁移与关键约束（CHECK/FK/索引）。
- 最小验收：schema 漂移检查通过；Alembic 成为唯一 DDL 入口。

2. `wp-runtime-pg-repository-switch-v1.0.0`
- 需要推进：仓储层切换 PG 权威读写，移除运行主链路 SQLite 分支。
- 最小验收：非 `postgresql://` fail-fast；主链路回归通过。

3. `wp-line-feedback-contract-pg-v1.0.0`
- 需要推进：回传契约改为 PG 引用真相源，禁止自由字段回写。
- 最小验收：contract tests 通过；回放记录可按 `workpackage_id/trace_id` 查询。

4. `wp-trust-evidence-index-phase1-v1.0.0`
- 需要推进：证据索引统一模型（task/workpackage/trace/replay）。
- 最小验收：至少 1 条全链路可回放并具审计字段。

5. `wp-pg-only-integration-baseline-v1.0.0`
- 需要推进：集成测试与验收脚本默认 PG-only，新增 SQLite 回流阻断。
- 最小验收：PG-only 集成门禁通过，回流检测触发可阻断。

6. `wp-observability-phase1-run-test-sql-map-v1.0.0`
- 需要推进：补齐 runtime summary/risk/tasks/workpackage-pipeline 指标映射与 SQL 查询口径。
- 最小验收：运行态 API 契约测试通过，指标可追溯到统一聚合口径。

7. `wp-dashboard-phase1-structured-rollup-v1.0.0`
- 需要推进：看板聚焦运行态结果，剥离研发过程状态噪声。
- 最小验收：支持空态引导 + 样例灌入后非空展示 + 任务下钻证据链。

8. `wp-address-canonical-pg-baseline-v1.0.0`
- 需要推进：建立 `addr_canonical` 质量基线与低置信策略。
- 最小验收：低置信模式 Top5 非空且可复核样本证据。

9. `wp-engineering-supervisor-phase1-audit-v1.0.0`
- 需要推进：输出工程边界与门禁合规审计（含 SQLite 回流、越界、证据缺失）。
- 最小验收：审计报告出具并形成阻断项清单与闭环状态。

10. `wp-orchestrator-phase1-crossline-closure-v1.0.0`
- 需要推进：汇总跨线结果，形成管理签发包（Go/No-Go）。
- 最小验收：决策包包含统一判定、风险项、证据链接、剩余阻塞项。

## 4. 角色分工（BM Master可直接派发）

1. PM（A-PM）
- 锁定 10 包 owner 与优先级。
- 冻结每包“开工准入三要素”：输入契约、测试清单、验收出口。
- 维护线性追踪映射（Linear Issue <-> PR <-> 证据）。

2. Architect（A-ARC）
- 审定统一 PG 多 schema 落地路径与仓储切换边界。
- 审定 runtime/observability 数据口径与 API 契约一致性。

3. Dev（A-DEV）
- 按“先测后改”原则落地：先失败用例，再实现修复，再回归。
- 优先完成底座包（DB/Repository/PG-only）后再推进观测展示层。

4. QA（A-QA）
- 建立发布门禁回归闭环：失败即阻断，关闭需证据。
- 固化 `release_gate` 与 `open_regression` 的自动校验输出。

5. SM（A-SM）
- 编排执行节奏，保证单周内不并发冲突底座改动。
- 跟踪依赖解除，推动 HOLD 包逐个转入 in-progress。

6. TW（A-TW）
- 输出统一发布说明与验收记录模板。
- 保证所有状态变更有可追溯文档与证据路径。

7. BM Master
- 统一派单与跨角色阻塞协调。
- 每轮汇总只认“单一发布判定规则”与“证据化验收结果”。

## 5. 开工准入门槛（统一模板）

每个 HOLD 包转 `in-progress` 前必须满足：

1. 已绑定唯一 owner（非“待分配”）。
2. 已明确输入契约与边界（schema/API/数据源）。
3. 已定义失败用例与回归用例（先失败后修复）。
4. 已定义验收产物路径（JSON/Markdown/测试报告）。
5. 已定义阻塞条件与解除条件。

## 6. 统一验收出口（跨角色共用）

1. 测试证据：`output/workpackages/*.report.json`
2. 验收证据：`output/acceptance/*.json` + `output/acceptance/*.md`
3. 看板证据：`output/dashboard/*.json`
4. 实施状态：`_bmad-output/implementation-artifacts/sprint-status.yaml`

## 7. BM Master 汇总建议（执行顺序）

1. 先清“口径冲突”：发布判定规则统一 + regression 关闭闭环。
2. 再清“底座阻塞”：DB/PG-only/Repository/Contract 四类包先开工。
3. 再推“观测呈现”：observability + dashboard 两类包。
4. 最后做“管理签发”：审计报告 + 跨线收口决策包。
