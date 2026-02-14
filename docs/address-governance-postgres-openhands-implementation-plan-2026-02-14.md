# 地址治理分阶段实施计划（面向完备能力）

## 1. 实施目标
- 建立“近期可交付 + 中长期可扩展”的治理工程路线，避免一次性重构。
- 近期（3周）完成可用闭环；中期（1-2月）完成规模化；后期（季度）完成完备能力。
- 以 OpenHands 统一执行层，逐步接入技能库、质量优化与策略治理。

## 2. 里程碑与验收

## 阶段A（Week 1）：打通最小闭环（必须完成）

### 工作项
- 建 PostgreSQL 基础表：`addr_batch/addr_raw/addr_canonical/addr_task_run`。
- 启用扩展：`pg_trgm`。
- 搭建 `governance-api` 基础接口：
  - `POST /v1/governance/tasks`
  - `GET /v1/governance/tasks/{task_id}`
  - `GET /v1/governance/tasks/{task_id}/result`
- 搭建 `governance-worker`（RQ）与 Redis。
- 落地 `address_core` 基础能力：`normalize + parse + score(v0)`。
- 新增 `AgentRuntimeAdapter` + `OpenHandsRuntime` 骨架并可返回结构化结果。

### 验收标准
- 单批次任务可从提交到完成，状态可追踪。
- 结果中包含 `canonical/confidence/evidence/ruleset_version`。
- 失败任务有错误码、可重试且有审计记录。

## 阶段B（Week 2）：提升有效性，降低人工量

### 工作项
- 实现匹配与召回：字典召回 + `pg_trgm` topK。
- 上线轻量去重：exact + 基础 fuzzy（同城同街阈值）。
- 增加人工复核接口：
  - `POST /v1/governance/reviews/{task_id}/decision`
- 增加规则集管理：
  - `GET/PUT /v1/governance/rulesets/{ruleset_id}`
  - `POST /v1/governance/rulesets/{ruleset_id}/publish`
- OpenHands 执行层补齐超时、重试、审计字段（`agent_run_id`）。

### 验收标准
- 相比 Week 1，自动通过率提升且误判受控。
- 可形成“自动通过/建议复核/强制复核”三层分流。
- 每条结果都可追溯到规则版本与执行证据。

## 阶段C（Week 3）：闭环调优与上线准备

### 工作项
- 增加抽样评估脚本（自动通过率、复核通过率、一致性、失败类型 TopN）。
- 形成参数变更单流程（人工确认应用）。
- 增加幂等与治理保障：
  - `idempotency_key`
  - 死信与补偿机制
  - 发布回滚策略
- 生产演练：故障注入、回滚演练、压测。

### 验收标准
- 一次完整灰度演练可回放。
- 出现 OpenHands 异常时可通过开关回退，不影响主流程可用性。
- 达到上线门槛：稳定性、审计完整性、人工负担可控。

## 3. 技术任务拆分

## 3.1 API/Schema
- Pydantic 模型：`TaskSubmitRequest/TaskStatusResponse/TaskResultResponse/ReviewDecisionRequest/RulesetModel`。
- JSON Schema：地址输入字段约束（长度、字符集、必填关系、枚举）与输出结构约束。

## 3.2 Worker/Pipeline
- 包结构：
  - `packages/address_core/normalize.py`
  - `packages/address_core/parse.py`
  - `packages/address_core/match.py`
  - `packages/address_core/score.py`
- Worker 作业拆分：`ingest_job`、`governance_job`、`review_reconcile_job`。

## 3.3 OpenHands 适配
- `AgentRuntimeAdapter` 接口定义。
- `OpenHandsRuntime` 实现。
- 执行结果标准化：`strategy/confidence/evidence/actions`。
- 配置项：`AGENT_RUNTIME`、超时、重试、并发。

## 3.4 数据库
- DDL 与迁移：Alembic 管理。
- 索引策略：trgm GIN + hash BTree。
- 保留审计表：`api_audit_log`、`agent_execution_log`。

## 4. 中期建设（1-2个月）

### 4.1 规模化能力
- 任务优先级队列与多租户隔离（按业务线/数据域）。
- 更完善的失败补偿（死信队列、自动重放、人工接管）。
- 规则灰度发布与指标对比（新旧规则并行评估）。

### 4.2 质量运营
- 建立质量看板：自动通过率、复核通过率、误判TopN、SLA。
- 问题聚类与规则建议池（人工审核后发布）。
- 建立小规模标注集，逐步替代代理指标。

### 4.3 OpenHands 深化
- 技能注册中心（skill metadata、schema、权限域）。
- 统一执行日志模型，支持跨任务检索与追踪。
- 执行层资源治理：并发配额、成本控制、超时预算。

## 5. 目标态建设（季度）

### 5.1 完备功能
- 离线批处理 + 准实时治理协同。
- 跨场景治理复用（地址、网点、场景图、画像数据）。
- 参数推荐与策略建议自动化（人工确认生效）。

### 5.2 编排增强（按需）
- 当流程复杂度上升时引入 LangGraph 或同类状态图编排。
- 将 Profile/Diagnose/Propose/Run/Evaluate/Decide 纳入标准工作流。

### 5.3 工程治理
- 可观测性体系完善：trace、指标、日志统一。
- 安全与合规：字段脱敏、审计不可篡改、操作分权。
- 灾备演练与跨环境回放（dev/stage/prod 一致性）。

## 6. 风险清单与应对

### 风险 1：OpenHands 接口不稳定
- 应对：熔断 + 重试 + 超时 + 运行时开关回退。

### 风险 2：地址脏数据导致低置信度积压
- 应对：加强 normalization 规则、补齐基础字典、人工复核优先队列。

### 风险 3：规则变更引发回归
- 应对：ruleset 版本化、灰度发布、变更审批。

## 7. 上线门禁（Go/No-Go）
- 核心接口 P95 延迟与错误率在可接受范围。
- 任务成功率与复核通过率达到基线。
- 审计字段完整率 100%。
- 具备一键回退执行层能力。

## 8. 责任分工建议
- 平台后端：API、队列、数据库迁移、审计。
- 算法/规则：normalize/parse/match/score 与 ruleset。
- Agent 工程：OpenHands 适配、执行观测、故障兜底。
- 业务运营：复核规则、灰度验收、质量看板。

## 9. 交付物清单（按阶段）

### 阶段A-C（3周）
- API 契约、核心 DDL、worker 任务链、复核闭环、运行审计。

### 中期（1-2个月）
- 质量看板、灰度发布、技能注册、失败补偿体系。

### 目标态（季度）
- 准实时能力、跨场景复用、编排增强、组织级治理闭环。

## 10. 下一步工作步骤拆解（立即启动）

## 10.1 启动原则
- 先打底座再叠能力：先数据与契约，再执行链路，再优化指标。
- 先可观测再扩规模：每个工作包都必须附带审计字段与失败可追踪能力。
- 先稳定再提效：阶段A完成前不并行推进高风险优化项。

## 10.2 工作包拆解（WBS）

### WP-01：数据底座与迁移脚手架（P0）
- 目标：建立 PostgreSQL + Alembic 可持续迁移能力。
- 子任务：
  - 定义 V1 DDL（batch/raw/canonical/task_run/ruleset/audit）。
  - 建立 Alembic 初始迁移脚本与回滚脚本。
  - 启用 `pg_trgm` 与核心索引。
- 交付：可在 dev 环境一键建库并通过最小读写验证。
- 依赖：无。

### WP-02：治理 API 契约与强校验（P0）
- 目标：交付可对接的稳定 API 契约。
- 子任务：
  - 定义 Pydantic 模型（提交、状态、结果、复核、规则集）。
  - 定义 JSON Schema 业务约束（地址字段长度/字符集/关系约束）。
  - 实现任务提交、状态查询、结果查询接口。
- 交付：OpenAPI 文档与接口测试样例。
- 依赖：WP-01。

### WP-03：Worker 与队列执行主链路（P0）
- 目标：形成异步执行闭环。
- 子任务：
  - RQ + Redis 接入。
  - 建立 `ingest_job/governance_job/review_reconcile_job`。
  - 统一任务状态机与失败重试策略。
- 交付：任务可异步执行并完整回写状态。
- 依赖：WP-01、WP-02。

### WP-04：OpenHands 执行适配器（P0）
- 目标：替换现有直连 LLM 调用链。
- 子任务：
  - 定义 `AgentRuntimeAdapter` 标准接口。
  - 实现 `OpenHandsRuntime` 与运行时开关。
  - 统一结构化输出：`strategy/confidence/evidence/agent_run_id`。
- 交付：在同一任务中可切换运行时并保持结果结构不变。
- 依赖：WP-03。

### WP-05：地址核心能力包（P1）
- 目标：完成一期可用治理能力。
- 子任务：
  - `normalize/parse/score(v0)`。
  - 字典召回 + `pg_trgm` 匹配 topK。
  - exact 去重 + 基础 fuzzy 去重。
- 交付：可输出 canonical 与 confidence 分层。
- 依赖：WP-03。

### WP-06：人工复核与规则发布（P1）
- 目标：形成人机闭环治理。
- 子任务：
  - 复核决策接口（approved/rejected/edited）。
  - 规则集草稿、发布、版本追踪。
  - 变更审计日志落库。
- 交付：复核结果可反哺规则版本。
- 依赖：WP-02、WP-03。

### WP-07：质量运营与上线门禁（P1）
- 目标：具备可上线评估能力。
- 子任务：
  - 抽样评估脚本（自动通过率、复核通过率、一致性、失败TopN）。
  - 灰度发布与回滚演练。
  - Go/No-Go 检查表执行。
- 交付：上线评审包（指标报告 + 风险结论）。
- 依赖：WP-04、WP-05、WP-06。

## 10.3 未来 10 个工作日执行节奏

### Day 1-2
- 完成 WP-01 DDL 与迁移基线。
- 输出接口契约初稿（WP-02）。

### Day 3-4
- 完成 WP-02 核心接口与 schema 校验。
- 启动 WP-03 队列执行主链路。

### Day 5-6
- 完成 WP-03 任务链路联调。
- 启动 WP-04 OpenHands 适配与开关。

### Day 7-8
- 完成 WP-05 地址核心能力包 V1。
- 上线复核与规则管理接口（WP-06）。

### Day 9-10
- 完成 WP-07 评估脚本与门禁检查。
- 输出阶段结项报告与下一迭代待办。

## 10.4 每个工作包的完成定义（DoD）
- 代码：主链路可运行，关键路径单测通过。
- 数据：核心表字段齐全，审计字段完整。
- 文档：接口契约、变更记录、回滚说明齐备。
- 运维：失败可重试、异常可定位、指标可观测。

## 10.5 风险前置检查（每日站会必看）
- 是否出现任务堆积或重试风暴。
- OpenHands 执行错误是否可分类、可回放。
- 复核队列是否超出运营承载阈值。
- 新规则发布是否附带可回滚版本。

## 10.6 阶段出口条件（进入中期建设前）
- A/B/C 阶段交付物全部完成并通过验收。
- 线上演练至少一次全链路成功。
- 关键指标达到基线且连续稳定 3 天。

## 11. WP-01 可执行任务清单（文件级）

## 11.1 目标
- 在不影响现有运行链路前提下，完成 PostgreSQL 数据底座与 Alembic 迁移能力初始化。
- 交付可重复执行、可回滚、可验证的数据库脚手架。

## 11.2 目录与文件落位

建议新增目录（如不存在）：
- `migrations/`
- `migrations/versions/`
- `database/postgres/`
- `database/postgres/sql/`

建议新增文件：
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/20260214_0001_init_addr_governance.py`
- `database/postgres/sql/001_enable_extensions.sql`
- `database/postgres/sql/002_init_tables.sql`
- `database/postgres/sql/003_init_indexes.sql`

## 11.3 DDL 拆解

### 任务 T1：扩展启用
- 文件：`database/postgres/sql/001_enable_extensions.sql`
- 内容：
  - `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
- 验收：查询 `pg_extension` 可见 `pg_trgm`。

### 任务 T2：核心表初始化
- 文件：`database/postgres/sql/002_init_tables.sql`
- 表清单：
  - `addr_batch`
  - `addr_raw`
  - `addr_canonical`
  - `addr_review`
  - `addr_ruleset`
  - `addr_task_run`
  - `api_audit_log`
  - `agent_execution_log`
- 必备字段要求：
  - 主键、创建/更新时间、`ruleset_version`、`trace_id`、`agent_run_id`（按表适配）。
- 验收：`
  SELECT table_name FROM information_schema.tables
  WHERE table_schema='public' AND table_name LIKE 'addr_%';
  ` 返回完整表集。

### 任务 T3：索引与约束
- 文件：`database/postgres/sql/003_init_indexes.sql`
- 索引清单：
  - `addr_raw(raw_hash)` BTree
  - `addr_raw(raw_text)` GIN(trgm)
  - `addr_canonical(canon_text)` GIN(trgm)
  - `addr_task_run(task_id, status)` 复合索引
- 约束建议：
  - `addr_review.review_status` 枚举约束
  - `addr_task_run.retry_count >= 0` 检查约束
- 验收：`\d+` 可见索引与约束。

## 11.4 Alembic 迁移脚本任务

### 任务 T4：初始化 Alembic 配置
- 文件：`migrations/env.py`、`migrations/script.py.mako`
- 要求：
  - 从环境变量读取 `DATABASE_URL`
  - 支持 `upgrade` 与 `downgrade`

### 任务 T5：首个版本迁移
- 文件：`migrations/versions/20260214_0001_init_addr_governance.py`
- 要求：
  - `upgrade()` 执行扩展、建表、索引、约束
  - `downgrade()` 可完整回滚
- 验收：
  - `upgrade head` 后表结构存在
  - `downgrade -1` 后对象可回退

## 11.5 配置与运行任务

### 任务 T6：配置样例
- 建议在 `config/` 下新增：
  - `database.postgres.example.env`
- 至少包含：
  - `DATABASE_URL`
  - `PG_POOL_SIZE`
  - `PG_MAX_OVERFLOW`

### 任务 T7：开发环境验收命令（文档化）
- 在实施记录中固定以下命令：
  - 迁移：`alembic upgrade head`
  - 回滚：`alembic downgrade -1`
  - 健康检查：执行最小 SQL 读写脚本

## 11.6 完成定义（WP-01 DoD）
- 结构：全部核心表、索引、约束创建成功。
- 迁移：升级/回滚双向可用。
- 可观测：失败时可定位具体 SQL 步骤。
- 文档：DDL 与迁移执行说明可被新成员复现。

## 12. WP-02 可执行任务清单（文件级）

## 12.1 目标
- 建立治理 API 的契约基线，确保输入输出可验证、可演进、可测试。
- 完成任务提交/状态查询/结果查询/人工复核/规则管理的第一版接口。

## 12.2 目录与文件落位

建议新增目录（如不存在）：
- `services/governance_api/`
- `services/governance_api/app/`
- `services/governance_api/app/routers/`
- `services/governance_api/app/models/`
- `services/governance_api/app/schemas/`
- `services/governance_api/tests/`

建议新增文件：
- `services/governance_api/app/main.py`
- `services/governance_api/app/routers/tasks.py`
- `services/governance_api/app/routers/reviews.py`
- `services/governance_api/app/routers/rulesets.py`
- `services/governance_api/app/models/task_models.py`
- `services/governance_api/app/models/review_models.py`
- `services/governance_api/app/models/ruleset_models.py`
- `services/governance_api/app/schemas/address_input.schema.json`
- `services/governance_api/app/schemas/address_output.schema.json`
- `services/governance_api/tests/test_tasks_api.py`
- `services/governance_api/tests/test_reviews_api.py`
- `services/governance_api/tests/test_rulesets_api.py`
- `services/governance_api/tests/test_schema_validation.py`

## 12.3 模型与契约任务

### 任务 T1：Pydantic 输入模型
- 文件：`app/models/task_models.py`
- 模型建议：
  - `TaskSubmitRequest`
  - `AddressRecordInput`
  - `TaskSubmitResponse`
- 关键字段：
  - `idempotency_key`、`batch_name`、`records`、`ruleset_id`。

### 任务 T2：Pydantic 输出模型
- 文件：`app/models/task_models.py`
- 模型建议：
  - `TaskStatusResponse`
  - `TaskResultResponse`
  - `CanonicalAddressResult`
  - `EvidenceSummary`

### 任务 T3：复核与规则模型
- 文件：`app/models/review_models.py`、`app/models/ruleset_models.py`
- 模型建议：
  - `ReviewDecisionRequest`
  - `ReviewDecisionResponse`
  - `RulesetPayload`
  - `RulesetPublishRequest`

## 12.4 路由与接口任务

### 任务 T4：任务路由
- 文件：`app/routers/tasks.py`
- 接口：
  - `POST /v1/governance/tasks`
  - `GET /v1/governance/tasks/{task_id}`
  - `GET /v1/governance/tasks/{task_id}/result`

### 任务 T5：复核路由
- 文件：`app/routers/reviews.py`
- 接口：
  - `POST /v1/governance/reviews/{task_id}/decision`

### 任务 T6：规则路由
- 文件：`app/routers/rulesets.py`
- 接口：
  - `GET /v1/governance/rulesets/{ruleset_id}`
  - `PUT /v1/governance/rulesets/{ruleset_id}`
  - `POST /v1/governance/rulesets/{ruleset_id}/publish`

### 任务 T7：应用装配
- 文件：`app/main.py`
- 要求：
  - 装配所有 router
  - 开启 OpenAPI 文档
  - 注册统一异常处理与请求日志中间件

## 12.5 Schema 校验任务

### 任务 T8：输入 JSON Schema
- 文件：`app/schemas/address_input.schema.json`
- 要求：
  - 地址字段长度、字符集、可选/必填关系
  - 批量提交时单条上限与批次上限约束

### 任务 T9：输出 JSON Schema
- 文件：`app/schemas/address_output.schema.json`
- 要求：
  - `canonical/confidence/strategy/evidence` 结构完整
  - `confidence` 范围约束（0~1）

### 任务 T10：运行时 schema 校验
- 落位：`tasks.py` 与结果序列化路径
- 要求：
  - 入参：Pydantic + JSON Schema 双校验
  - 出参：关键响应结构校验（至少 result 接口）

## 12.6 测试任务（最小集）

### 任务 T11：接口单测
- 文件：
  - `tests/test_tasks_api.py`
  - `tests/test_reviews_api.py`
  - `tests/test_rulesets_api.py`
- 覆盖：
  - 成功路径
  - 参数缺失/格式错误
  - task_id/ruleset_id 不存在

### 任务 T12：schema 校验单测
- 文件：`tests/test_schema_validation.py`
- 覆盖：
  - 脏地址输入被拒绝
  - 合法输入通过
  - 输出不合规时触发错误

## 12.7 验收命令建议
- 启动 API：`uvicorn app.main:app --reload`
- 执行测试：`pytest services/governance_api/tests -q`
- 校验 OpenAPI：访问 `/docs` 并导出 schema 快照。

## 12.8 完成定义（WP-02 DoD）
- 契约：OpenAPI 与模型一致，无破坏性字段漂移。
- 校验：Pydantic + JSON Schema 双层校验生效。
- 测试：核心接口与校验单测通过。
- 审计：请求与错误链路可追踪（trace_id/task_id）。

## 13. WP-03 可执行任务清单（文件级）

## 13.1 目标
- 建立异步执行主链路，确保任务可排队、可执行、可重试、可追踪。
- 将 API 与执行解耦，统一由 worker 管理执行状态与结果回写。

## 13.2 目录与文件落位

建议新增目录（如不存在）：
- `services/governance_worker/`
- `services/governance_worker/app/`
- `services/governance_worker/app/jobs/`
- `services/governance_worker/app/core/`
- `services/governance_worker/tests/`

建议新增文件：
- `services/governance_worker/app/worker.py`
- `services/governance_worker/app/core/queue.py`
- `services/governance_worker/app/core/task_state.py`
- `services/governance_worker/app/jobs/ingest_job.py`
- `services/governance_worker/app/jobs/governance_job.py`
- `services/governance_worker/app/jobs/review_reconcile_job.py`
- `services/governance_worker/app/jobs/result_persist_job.py`
- `services/governance_worker/tests/test_task_state_machine.py`
- `services/governance_worker/tests/test_governance_job_flow.py`
- `services/governance_worker/tests/test_retry_and_deadletter.py`

## 13.3 队列与状态机任务

### 任务 T1：队列连接与任务提交
- 文件：`app/core/queue.py`
- 要求：
  - Redis 连接管理（超时、重连、连接池）
  - 任务入队 API（含 `task_id`、`trace_id`、优先级）

### 任务 T2：任务状态机
- 文件：`app/core/task_state.py`
- 状态建议：
  - `PENDING` -> `RUNNING` -> `SUCCEEDED`
  - `PENDING`/`RUNNING` -> `FAILED`
  - `FAILED` -> `RETRYING` -> `RUNNING`
  - `FAILED` -> `DEAD_LETTER`
- 要求：非法状态转移必须拒绝并记录审计。

### 任务 T3：Worker 入口
- 文件：`app/worker.py`
- 要求：
  - 注册全部 job
  - 启动参数支持并发、队列名、日志级别
  - 捕获未处理异常并写入 `addr_task_run`

## 13.4 作业链任务

### 任务 T4：入库预处理作业
- 文件：`app/jobs/ingest_job.py`
- 职责：
  - 校验任务输入
  - 写入 `addr_raw`
  - 初始化 `addr_task_run`

### 任务 T5：治理主作业
- 文件：`app/jobs/governance_job.py`
- 职责：
  - 调用 `address_core` 与 `AgentRuntimeAdapter`
  - 产出 `canonical/confidence/evidence`
  - 写回 `addr_canonical`

### 任务 T6：复核回灌作业
- 文件：`app/jobs/review_reconcile_job.py`
- 职责：
  - 处理人工 `approved/rejected/edited`
  - 更新最终结果状态与规则反馈计数

### 任务 T7：结果持久化与审计
- 文件：`app/jobs/result_persist_job.py`
- 职责：
  - 统一写入执行摘要
  - 记录 `agent_run_id`、失败原因、耗时、重试次数

## 13.5 可靠性任务

### 任务 T8：重试策略
- 位置：`governance_job.py` + `task_state.py`
- 要求：
  - 指数退避重试
  - 最大重试次数可配置
  - 最终进入死信队列

### 任务 T9：死信机制
- 位置：`queue.py` / `retry_and_deadletter` 测试
- 要求：
  - 死信可查询
  - 支持人工重放接口预留

### 任务 T10：幂等执行
- 要求：
  - 依据 `idempotency_key + task_payload_hash` 去重
  - 重复请求不重复执行

## 13.6 测试任务（最小集）
- `test_task_state_machine.py`：状态转移合法性与边界。
- `test_governance_job_flow.py`：从入队到结果落库的主链路。
- `test_retry_and_deadletter.py`：重试与死信行为。

## 13.7 验收命令建议
- 启动 worker：`python -m services.governance_worker.app.worker`
- 执行测试：`pytest services/governance_worker/tests -q`
- 冒烟：提交一个最小任务，确认状态最终到 `SUCCEEDED/FAILED`。

## 13.8 完成定义（WP-03 DoD）
- 链路：任务从入队到落库全链路贯通。
- 稳定：失败重试、死信、异常审计生效。
- 一致：状态机无非法跃迁。
- 可观测：trace_id/task_id/agent_run_id 全链路可查。

## 14. WP-04 可执行任务清单（文件级）

## 14.1 目标
- 用 OpenHands 执行层替换现有直连 LLM 调用链，并保持对上游接口无破坏。
- 统一执行结果结构，形成可回退、可观测、可测试的运行时适配层。

## 14.2 目录与文件落位

建议新增目录（如不存在）：
- `packages/agent_runtime/`
- `packages/agent_runtime/adapters/`
- `packages/agent_runtime/models/`
- `packages/agent_runtime/tests/`

建议新增文件：
- `packages/agent_runtime/adapters/base.py`
- `packages/agent_runtime/adapters/openhands_runtime.py`
- `packages/agent_runtime/adapters/legacy_runtime.py`
- `packages/agent_runtime/runtime_selector.py`
- `packages/agent_runtime/models/runtime_result.py`
- `packages/agent_runtime/tests/test_runtime_selector.py`
- `packages/agent_runtime/tests/test_openhands_runtime_contract.py`
- `packages/agent_runtime/tests/test_runtime_fallback.py`

## 14.3 适配器任务

### 任务 T1：统一接口定义
- 文件：`adapters/base.py`
- 接口：
  - `run_task(task_context: dict, ruleset: dict) -> RuntimeResult`
- 要求：
  - 同步返回结构体
  - 标准错误对象

### 任务 T2：OpenHands Runtime 实现
- 文件：`adapters/openhands_runtime.py`
- 要求：
  - 封装 OpenHands 调用细节
  - 支持超时、重试、请求上下文
  - 产出 `strategy/confidence/evidence/actions/agent_run_id`

### 任务 T3：Legacy 兜底实现
- 文件：`adapters/legacy_runtime.py`
- 要求：
  - 保留紧急回退路径
  - 行为与输出结构与 OpenHands 对齐

### 任务 T4：运行时选择器
- 文件：`runtime_selector.py`
- 要求：
  - 依据 `AGENT_RUNTIME` 选择实现
  - 非法值时默认回退策略可配置

## 14.4 结果模型与契约

### 任务 T5：RuntimeResult 模型
- 文件：`models/runtime_result.py`
- 字段：
  - `strategy`
  - `canonical`
  - `confidence`
  - `evidence`
  - `actions`
  - `agent_run_id`
  - `raw_response`（可选，用于审计）

### 任务 T6：契约校验
- 要求：
  - worker 只消费 `RuntimeResult`
  - 禁止 worker 直接依赖 OpenHands SDK 对象

## 14.5 集成任务

### 任务 T7：接入 governance_job
- 位置：`services/governance_worker/app/jobs/governance_job.py`
- 要求：
  - 通过 `runtime_selector` 注入运行时
  - 错误分类：可重试/不可重试

### 任务 T8：审计落库
- 位置：`result_persist_job.py` 或审计服务
- 要求：
  - 持久化 `agent_run_id/runtime/runtime_latency`
  - 记录 fallback 事件

## 14.6 测试任务（最小集）
- `test_runtime_selector.py`：运行时选择正确。
- `test_openhands_runtime_contract.py`：输出结构完整合法。
- `test_runtime_fallback.py`：OpenHands 异常时 fallback 生效。

## 14.7 验收命令建议
- 运行适配层测试：`pytest packages/agent_runtime/tests -q`
- 集成冒烟：提交同一任务分别跑 `AGENT_RUNTIME=openhands` 与 `legacy`。
- 比对：检查两种运行时输出结构一致。

## 14.8 完成定义（WP-04 DoD）
- 替换：主链路默认走 OpenHands。
- 回退：出现异常时可一键切换至 legacy。
- 一致：输出契约稳定，无上游破坏。
- 审计：执行来源、时延、错误分类可追踪。

## 15. WP-05 可执行任务清单（文件级）

## 15.1 目标
- 建立地址治理核心能力包 `address_core`，形成可解释、可复用、可测试的标准处理链路。
- 完成一期能力：标准化、解析、匹配、打分、去重、置信度分层。

## 15.2 目录与文件落位

建议新增目录（如不存在）：
- `packages/address_core/`
- `packages/address_core/rules/`
- `packages/address_core/dictionaries/`
- `packages/address_core/tests/`

建议新增文件：
- `packages/address_core/normalize.py`
- `packages/address_core/parse.py`
- `packages/address_core/match.py`
- `packages/address_core/score.py`
- `packages/address_core/dedup.py`
- `packages/address_core/pipeline.py`
- `packages/address_core/types.py`
- `packages/address_core/rules/ruleset_config.example.json`
- `packages/address_core/dictionaries/alias_mapping.example.json`
- `packages/address_core/dictionaries/admin_division_minimal.example.json`
- `packages/address_core/tests/test_normalize.py`
- `packages/address_core/tests/test_parse.py`
- `packages/address_core/tests/test_match_score.py`
- `packages/address_core/tests/test_dedup.py`
- `packages/address_core/tests/test_pipeline_smoke.py`

## 15.3 能力模块任务

### 任务 T1：类型与数据结构定义
- 文件：`types.py`
- 结构建议：
  - `RawAddressRecord`
  - `CanonicalAddress`
  - `MatchCandidate`
  - `EvidenceItem`
  - `GovernanceResult`

### 任务 T2：标准化模块
- 文件：`normalize.py`
- 能力：
  - 全半角、空白、标点归一
  - 别名映射（路/街/大道等）
  - 数字表达统一（中文数字与阿拉伯数字）

### 任务 T3：结构化解析模块
- 文件：`parse.py`
- 能力：
  - 省/市/区/街道/路名/门牌/楼栋单元房号拆解
  - 解析失败输出 partial + 错误标签

### 任务 T4：候选匹配模块
- 文件：`match.py`
- 能力：
  - 字典召回（行政区、常见地名、POI）
  - `pg_trgm` 相似召回 topK
  - 多候选结构化输出

### 任务 T5：打分与置信度模块
- 文件：`score.py`
- 能力：
  - 字段一致性分
  - 文本相似分
  - 规则命中加权
  - 输出 `confidence` 与 `strategy`

### 任务 T6：去重模块
- 文件：`dedup.py`
- 能力：
  - exact 去重（hash）
  - fuzzy 去重（同城同街 + 相似阈值）

### 任务 T7：管道编排模块
- 文件：`pipeline.py`
- 能力：
  - 串联 normalize -> parse -> match -> score -> dedup
  - 统一产出 `GovernanceResult`

## 15.4 配置与字典任务

### 任务 T8：规则配置模板
- 文件：`rules/ruleset_config.example.json`
- 内容建议：
  - `thresholds`（`t_high/t_low`）
  - `weights`（字段权重）
  - `switches`（规则开关）

### 任务 T9：最小字典模板
- 文件：`dictionaries/*.example.json`
- 内容建议：
  - 行政区最小集合
  - 地址常见别名映射

## 15.5 集成任务

### 任务 T10：接入 governance_job
- 位置：`services/governance_worker/app/jobs/governance_job.py`
- 要求：
  - 使用 `pipeline.run(record, ruleset)`
  - 将 `evidence` 与 `confidence` 写回 `addr_canonical`

### 任务 T11：结果分层
- 要求：
  - `confidence >= t_high` 自动通过
  - `t_low <= confidence < t_high` 建议复核
  - `< t_low` 强制复核

## 15.6 测试任务（最小集）
- `test_normalize.py`：归一化规则正确性。
- `test_parse.py`：结构解析与 partial 行为。
- `test_match_score.py`：候选召回与评分输出。
- `test_dedup.py`：exact/fuzzy 去重边界。
- `test_pipeline_smoke.py`：整链路冒烟。

## 15.7 验收命令建议
- 执行单测：`pytest packages/address_core/tests -q`
- 冒烟：使用 50-100 条样本跑 `pipeline` 并输出统计。
- 指标：自动通过率、建议复核率、强制复核率总和为 100%。

## 15.8 完成定义（WP-05 DoD）
- 能力：一期核心能力全部可运行。
- 质量：模块测试通过且覆盖关键脏数据场景。
- 可解释：每条结果都附 evidence。
- 可配置：阈值、权重、规则开关均可外置配置。

## 16. WP-06 可执行任务清单（文件级）

## 16.1 目标
- 打通人工复核与规则发布闭环，实现“人机协同治理”与可回放变更管理。
- 让复核结果能够反馈规则迭代，形成持续优化机制。

## 16.2 目录与文件落位

建议新增目录（如不存在）：
- `services/governance_api/app/services/`
- `services/governance_api/app/repositories/`
- `services/governance_api/app/policies/`
- `services/governance_api/tests/fixtures/`

建议新增文件：
- `services/governance_api/app/services/review_service.py`
- `services/governance_api/app/services/ruleset_service.py`
- `services/governance_api/app/repositories/review_repository.py`
- `services/governance_api/app/repositories/ruleset_repository.py`
- `services/governance_api/app/policies/ruleset_publish_policy.py`
- `services/governance_api/tests/test_review_service.py`
- `services/governance_api/tests/test_ruleset_publish_flow.py`
- `services/governance_api/tests/test_ruleset_gray_release.py`

## 16.3 人工复核任务

### 任务 T1：复核服务实现
- 文件：`services/review_service.py`
- 能力：
  - 处理 `approved/rejected/edited`
  - 支持 `final_canon_text` 覆盖
  - 写入 `addr_review` 与 `api_audit_log`

### 任务 T2：复核仓储实现
- 文件：`repositories/review_repository.py`
- 能力：
  - 复核记录创建/查询/更新
  - 根据 task_id 回写结果状态

### 任务 T3：复核结果回灌
- 位置：worker 的 `review_reconcile_job`
- 能力：
  - 更新最终 canonical 状态
  - 累积规则反馈计数（命中/误判）

## 16.4 规则发布任务

### 任务 T4：规则集服务实现
- 文件：`services/ruleset_service.py`
- 能力：
  - 规则草稿保存
  - 发布新版本并生成版本号
  - 标记 active ruleset

### 任务 T5：发布策略与校验
- 文件：`policies/ruleset_publish_policy.py`
- 能力：
  - 发布前 schema/字段/阈值合法性检查
  - 阻止破坏性配置直接发布

### 任务 T6：灰度发布（一期最小）
- 能力：
  - 支持按批次或比例灰度
  - 记录灰度窗口、对比指标、回滚点

## 16.5 审计与治理任务

### 任务 T7：发布审计
- 要求：
  - 每次发布记录 `ruleset_version/operator/reason/diff`
  - 支持审计查询与回放

### 任务 T8：复核运营视图（API）
- 建议接口：
  - `GET /v1/governance/reviews/pending`
  - `GET /v1/governance/reviews/stats`

## 16.6 测试任务（最小集）
- `test_review_service.py`：三种复核决策路径。
- `test_ruleset_publish_flow.py`：草稿到发布全流程。
- `test_ruleset_gray_release.py`：灰度发布与回滚。

## 16.7 验收命令建议
- 执行测试：`pytest services/governance_api/tests -q`
- 发布冒烟：创建规则草稿 -> 发布 -> 灰度 -> 回滚。
- 复核冒烟：对同一 task_id 执行 edited，验证结果回写。

## 16.8 完成定义（WP-06 DoD）
- 闭环：复核与规则发布全链路可执行。
- 安全：发布前校验生效，破坏性配置被拦截。
- 可回放：规则发布与复核决策全量可追溯。
- 可运营：待复核与发布状态可查询、可统计。

## 17. WP-07 可执行任务清单（文件级）

## 17.1 目标
- 建立质量运营与上线门禁体系，确保系统从“可运行”升级到“可上线、可持续优化”。
- 形成指标采集、评估报告、灰度决策、回滚演练的标准流程。

## 17.2 目录与文件落位

建议新增目录（如不存在）：
- `observability/governance_quality/`
- `scripts/quality/`
- `services/governance_api/app/routers/ops.py`
- `services/governance_api/app/services/quality_service.py`
- `services/governance_api/tests/test_quality_ops_api.py`

建议新增文件：
- `observability/governance_quality/metrics_definition.yaml`
- `observability/governance_quality/go_no_go_checklist.md`
- `scripts/quality/run_quality_evaluation.py`
- `scripts/quality/run_gray_release_check.py`
- `scripts/quality/run_rollback_drill.py`
- `services/governance_api/app/services/quality_service.py`
- `services/governance_api/app/routers/ops.py`
- `services/governance_api/tests/test_quality_ops_api.py`
- `services/governance_worker/tests/test_quality_metrics_emission.py`

## 17.3 指标体系任务

### 任务 T1：指标定义
- 文件：`observability/governance_quality/metrics_definition.yaml`
- 指标最小集：
  - 自动通过率
  - 建议复核率
  - 强制复核率
  - 复核通过率
  - 任务成功率
  - P95/P99 处理时延
  - 失败类型 TopN

### 任务 T2：指标采集落地
- 位置：worker 执行链路 + API 服务层
- 要求：
  - 每个任务结束时上报核心指标
  - 按 ruleset_version、runtime、批次维度聚合

### 任务 T3：质量评估脚本
- 文件：`scripts/quality/run_quality_evaluation.py`
- 输出：
  - JSON 报告（机器可读）
  - Markdown 摘要（评审可读）

## 17.4 上线门禁任务

### 任务 T4：Go/No-Go 检查表
- 文件：`observability/governance_quality/go_no_go_checklist.md`
- 检查项：
  - 成功率阈值
  - 时延阈值
  - 审计完整率
  - 回退可用性
  - 人工复核队列容量

### 任务 T5：灰度验证脚本
- 文件：`scripts/quality/run_gray_release_check.py`
- 要求：
  - 比较新旧 ruleset/runtime 指标差异
  - 超阈值自动阻断发布

### 任务 T6：回滚演练脚本
- 文件：`scripts/quality/run_rollback_drill.py`
- 要求：
  - 模拟 OpenHands 异常
  - 验证一键回退到 legacy runtime
  - 记录恢复耗时与恢复成功率

## 17.5 运营接口任务

### 任务 T7：质量运营 API
- 文件：`services/governance_api/app/routers/ops.py`
- 接口建议：
  - `GET /v1/governance/quality/metrics`
  - `GET /v1/governance/quality/report/latest`
  - `POST /v1/governance/quality/go-no-go/evaluate`

### 任务 T8：质量服务实现
- 文件：`services/governance_api/app/services/quality_service.py`
- 能力：
  - 聚合指标
  - 生成评估结论
  - 输出建议动作（继续灰度/暂停发布/触发回滚）

## 17.6 测试任务（最小集）
- `test_quality_metrics_emission.py`：核心指标是否按任务正确上报。
- `test_quality_ops_api.py`：运营接口可用性与返回结构。
- 脚本冒烟：
  - `run_quality_evaluation.py`
  - `run_gray_release_check.py`
  - `run_rollback_drill.py`

## 17.7 验收命令建议
- 指标测试：`pytest services/governance_worker/tests/test_quality_metrics_emission.py -q`
- 运营 API 测试：`pytest services/governance_api/tests/test_quality_ops_api.py -q`
- 质量评估：`python scripts/quality/run_quality_evaluation.py --latest`
- 门禁评估：`python scripts/quality/run_gray_release_check.py --ruleset new`
- 回滚演练：`python scripts/quality/run_rollback_drill.py`

## 17.8 完成定义（WP-07 DoD）
- 可见：关键质量指标可查询、可导出、可对比。
- 可控：发布前门禁可自动判定 Go/No-Go。
- 可恢复：回滚演练成功且恢复时长满足门槛。
- 可运营：每周可产出标准化质量报告并指导规则优化。
