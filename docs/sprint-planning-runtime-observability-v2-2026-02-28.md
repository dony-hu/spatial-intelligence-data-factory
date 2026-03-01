# Sprint Planning - 运行态可观测 V2（2026-02-28）

## 1. 规划信息

- 规划版本：v1.0
- 规划日期：2026-02-28
- 上游输入：
  - `docs/epic-runtime-observability-v2-2026-02-28.md`
  - `docs/prd-runtime-observability-dashboard-2026-02-28.md`
  - `docs/architecture/architecture-runtime-observability-v2-2026-02-28.md`
- 规划目标：将 Epic 拆解为可执行 Sprint 与可验收门禁，直接进入开发执行。

## 2. Sprint 分段目标

1. Sprint-A（MVP，业务可见价值）：完成 `S2-1~S2-4 + S2-14`，上线运行态观测页面最小闭环。
2. Sprint-B（稳定运营增强）：完成 `S2-5~S2-9`，补齐可靠性、性能与单租户最小合规能力。

## 3. Sprint-A Backlog（MVP，Must）

| ID | Story | 目标 | 主要交付物 | 验收标准 |
|---|---|---|---|---|
| S2-1 | 运行态聚合 API 与指标口径统一 | 建立 `runtime/*` 核心 API 与统一口径 | `services/governance_api/app/routers/observability.py`、`services/governance_api/app/services/*`、`services/governance_api/tests/test_runtime_observability_api_contract.py` | `summary/risk-distribution/version-compare/tasks` 契约测试通过 |
| S2-2 | 运行态页面重构与交互联动 | 页面从研发视角切换为运行态视角 | `services/governance_api/app/routers/lab.py`、`tests/web_e2e/*` | KPI/风险/版本/明细联动可用，空态可引导 |
| S2-3 | 地址治理样例包灌入与空态引导 | 构造 60+ 样例，保证页面非空 | `scripts/*seed*`、`services/governance_api/tests/*` | 灌入后指标落入目标区间，页面非空 |
| S2-4 | 任务下钻追溯与回归验收闭环 | 完成任务级 evidence/review/audit 回放 | `services/governance_api/app/routers/observability.py`、`services/governance_api/tests/*` | 任一任务可下钻并形成验收证据 |
| S2-14 | 新增治理包链路观测与验收闭环 | 观测 CLI/Agent/LLM/Runtime 全链路并支持弹窗下钻 | `services/governance_api/app/routers/observability.py`、`services/governance_api/app/services/*`、`services/governance_api/tests/test_runtime_workpackage_*`、`tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py` | 三个新 API 契约通过；页面可观测完整链路与 receipt；脱敏/RBAC 正确 |

## 4. Sprint-B Backlog（Should）

| ID | Story | 目标 | 主要交付物 | 验收标准 |
|---|---|---|---|---|
| S2-5 | SLI/SLO 与告警策略闭环 | 定义可靠性指标与告警升级闭环 | `services/governance_api/app/services/*`、`services/governance_api/tests/*` | SLI 可查询、SLO 违约可告警并 ACK |
| S2-6 | 数据新鲜度与端到端延迟观测 | 建立 ingestion->aggregation->UI 延迟观测 | `services/governance_api/app/services/*`、`tests/*` | `event_lag/aggregation_lag/data_age` 可见且可告警 |
| S2-7 | 地址治理质量漂移与异常检测 | 建立质量退化检测与下钻定位 | `services/governance_api/app/services/*`、`tests/*` | 漂移异常可识别且可跳转样本任务 |
| S2-8 | 观测数据保留分区与性能治理 | 稳定高数据量下查询性能 | `migrations/versions/*`、`services/governance_api/tests/*` | 聚合/下钻性能达到目标阈值 |
| S2-9 | 权限脱敏与审计合规（单租户） | 补齐单租户最小 RBAC + 脱敏 | `services/governance_api/app/routers/*`、`tests/*` | 未授权拒绝、敏感字段脱敏、审计可追踪 |

## 5. 执行顺序与并行策略

1. 顺序主链：`S2-1 -> S2-2 -> S2-3 -> S2-4 -> S2-14 -> S2-5 -> S2-6 -> S2-7 -> S2-8 -> S2-9`
2. 可并行建议：
   - `S2-5` 与 `S2-6` 可并行
   - `S2-7` 可在 `S2-4` 完成后并行推进
3. 阻塞规则：关键依赖失败直接 `blocked`，禁止 fallback 与 Dummy runtime 绕行。

## 6. 门禁对齐（Must / Should / Later）

1. Must（阻塞上线）：
   - `S2-1~S2-4 + S2-14` 全部通过
   - `runtime/*` 契约测试通过
   - `workpackage-pipeline/workpackage-events/llm-interactions` 契约测试通过
   - No-Fallback 主链路通过
2. Should（可灰度）：
   - `S2-5~S2-8`
3. Later（可延期）：
   - 多租户权限扩展（不在本 Epic）

## 7. 测试与质量策略

1. TDD 顺序固定：先失败用例 -> 再实现 -> 最后回归。
2. 验收证据固定产物：JSON + Markdown。
3. 主线链路默认 PG 真实口径，关键失败必须显式阻塞。

## 8. DoD（Sprint Planning）

1. Sprint-A 与 Sprint-B 均有清晰 Story、交付物、验收标准。
2. 执行顺序、并行策略、门禁规则明确。
3. 可直接进入 `dev-story` 执行。

## 9. 迭代进展（2026-02-28 刷新）

### 9.1 已完成

1. `S2-14` 新增运行态 API：`workpackage-pipeline/workpackage-events/llm-interactions` 已落地并通过契约测试。
2. 运行态页面已新增“治理包链路观测”板块，并支持链路事件弹窗。
3. 已提供 `seed-workpackage-demo` 一键灌入能力，便于页面演示与回归。

### 9.2 进行中

1. 真实链路长压验证（连续多批次）与异常样本补充。

### 9.3 本轮新增完成（2026-03-01）

1. Factory CLI / Factory Agent 已补充真实链路观测埋点（created/packaged/submitted/accepted/running/finished + llm_request/llm_response）。
2. `workpackage-pipeline` 已补齐 PRD 明细字段：`checksum/skills_count/artifact_count/submit_status/runtime_receipt_id`。
3. WebUI E2E 已强化并通过：覆盖“灌入样例 -> 列表非空 -> 点击工作包 -> 弹窗时间线”。
4. `S2-14` 验收证据已归档：
   - `docs/acceptance/s2-14-runtime-observability-acceptance-2026-03-01.json`
   - `docs/acceptance/s2-14-runtime-observability-acceptance-2026-03-01.md`

### 9.4 剩余门禁

1. 验证真实链路事件可直接驱动页面，无需依赖 seed 才有数据。
2. 补齐 `S2-14` 验收证据（Markdown + JSON）并归档。
