# Epic3 状态评审与 Task 清单（2026-03-02）

## 评审结论

Epic3 在 `sprint-status` 已标记为 `done`，但当前证据链未完全闭合，建议状态调整为“可收口待会签（review-ready）”，先完成 P0 任务再执行最终 `done` 会签。

## 基于用例刷新

已按 `services/governance_api/tests/test_runtime_workpackage_events_api_contract.py` 执行一次 E2E 验证（`1 passed`），结论如下：

1. `workpackage-events` 中文可读字段（`source_zh/event_type_zh/status_zh/description_zh`）已自动化覆盖。
2. `payload_summary.pipeline_stage_zh` 非空约束已自动化覆盖。
3. 该结果可作为 `S2-14` 可读性验收证据补充，但不替代 `S2-5~S2-9` Full DoD 证据缺口。

## Findings（按严重度）

### P0-F1：状态与证据不一致，存在“已完成但证据未闭环”风险

- 现状：
  1. `epic-3` 与 `3-1~3-9/3-14` 在状态文件中均为 `done`。
  2. `docs/acceptance/` 仅存在 `S2-14` 验收文件，缺失 `S2-5~S2-9` 的 Full DoD 验收包。
- 证据：
  1. `_bmad-output/implementation-artifacts/sprint-status.yaml`
  2. `docs/acceptance/s2-14-runtime-observability-acceptance-2026-03-01.md`
  3. `docs/acceptance/s2-14-runtime-observability-acceptance-2026-03-01.json`

### P0-F2：Story 工件覆盖不完整，追溯链断点（已关闭，2026-03-02）

- 处理结果：
  1. `3-1/3-2/3-3/3-4/3-14` implementation 工件已补齐。
  2. 每个文件已包含 `Status/Tasks/测试命令/File List/证据路径`。
- 验证证据：
  1. `_bmad-output/implementation-artifacts/3-1-runtime-aggregation-api-and-metrics-unification.md`
  2. `_bmad-output/implementation-artifacts/3-2-runtime-observability-page-refactor-and-interaction-linkage.md`
  3. `_bmad-output/implementation-artifacts/3-3-address-governance-seed-pack-and-empty-state-guidance.md`
  4. `_bmad-output/implementation-artifacts/3-4-task-drilldown-traceability-and-regression-acceptance-closure.md`
  5. `_bmad-output/implementation-artifacts/3-14-new-governance-workpackage-pipeline-observability-and-acceptance-closure.md`

### P1-F3：Story 内部状态口径冲突（`Status: done` vs `Change Log: review`）

- 现状：`3-5~3-9` 文件顶部为 `Status: done`，但变更记录写“推进至 review”。
- 风险：BM Master 无法据此做自动化汇总与准确会签。
- 证据：
  1. `_bmad-output/implementation-artifacts/3-5-sli-slo-and-alert-policy-closure.md`
  2. `_bmad-output/implementation-artifacts/3-6-data-freshness-and-end-to-end-latency-observability.md`
  3. `_bmad-output/implementation-artifacts/3-7-address-governance-quality-drift-and-anomaly-detection.md`
  4. `_bmad-output/implementation-artifacts/3-8-observability-data-retention-partition-and-query-performance-governance.md`
  5. `_bmad-output/implementation-artifacts/3-9-observability-permission-masking-and-audit-compliance.md`

### P1-F4：工作流状态与 Epic3 完成态不匹配

- 现状：`docs/bmm-workflow-status.yaml` 仍显示 `current_workflow: sprint-planning` 且 `recommendation.next_workflow: dev-story`。
- 风险：后续角色会继续“开发推进”而非“收口会签”。
- 证据：
  1. `docs/bmm-workflow-status.yaml`

## Task 清单（可直接建单）

| Task ID | 优先级 | 任务 | Owner | 交付物 | 验收标准 |
|---|---|---|---|---|---|
| E3-RV-001（已完成） | P0 | 补齐 `3-1/3-2/3-3/3-4/3-14` implementation 工件 | A-DEV | `_bmad-output/implementation-artifacts/3-*.md` | 每个 story 含 Status/Tasks/测试命令/File List/证据路径 |
| E3-RV-002 | P0 | 补齐 `S2-5~S2-9` 验收证据（JSON+MD） | A-QA | `docs/acceptance/s2-5*.json/.md` ... `s2-9*.json/.md` | Full DoD 可独立判定，含 No-Fallback 与残余风险 |
| E3-RV-003 | P0 | 生成 Epic3 Full 汇总验收包 | A-QA | `docs/acceptance/epic3-full-acceptance-2026-03-02.json` + `.md` | 覆盖 `S2-1~S2-9 + S2-14`，可直接用于 Go/No-Go |
| E3-RV-004 | P1 | 统一 `3-5~3-9` 状态口径（正文/变更日志/状态文件） | A-SM + A-PM | 状态对齐记录 + 更新 `sprint-status.yaml` | 无 `done/review` 冲突 |
| E3-RV-005 | P1 | 运行 Epic3 核心回归矩阵并出单份回归摘要 | A-QA + A-DEV | `output/test-reports/epic-3-regression-summary-*.md` | API 契约/RBAC/UI E2E/No-Fallback 有结论与阻断判定 |
| E3-RV-006 | P1 | 更新 BMAD workflow 状态到“收口路径” | A-SM | 更新 `docs/bmm-workflow-status.yaml` | `recommendation.next_workflow` 指向收口而非继续 dev |
| E3-RV-007 | P1 | Epic3 收口会签并定版状态 | BM Master + A-ARC + A-QA + A-PM | 更新评审纪要 + `sprint-status.yaml` | 会签结论、时间戳、阻塞项、责任人齐全 |
| E3-RV-008 | P1 | Linear 映射补齐（任务与 PR 绑定） | A-PM | Linear issue 清单 + PR 链接清单 | 所有 E3-RV 任务均可追踪 |

## 推荐执行顺序

`E3-RV-001 -> E3-RV-002 -> E3-RV-003 -> E3-RV-004 -> E3-RV-005 -> E3-RV-006 -> E3-RV-007`，`E3-RV-008` 并行。

## 执行记录

- 2026-03-02（A-DEV）：执行 `E3-RV-001` 复核，通过以下回归验证：
  - `PYTHONPATH=. DATABASE_URL='postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory' ./.venv/bin/pytest -q services/governance_api/tests/test_runtime_observability_api_contract.py services/governance_api/tests/test_runtime_observability_view.py services/governance_api/tests/test_runtime_workpackage_seed_demo.py services/governance_api/tests/test_runtime_workpackage_events_api_contract.py services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py services/governance_api/tests/test_runtime_llm_interactions_api_contract.py services/governance_api/tests/test_runtime_workpackage_observability_rbac.py tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py tests/web_e2e/test_runtime_observability_upload_ui.py --maxfail=1`
  - 结果：`14 passed`

## PM 工作项合并（来自 `pm-cross-role-unified-push-2026-03-02.md`）

### PM-M1：统一发布判定口径（SSOT）

- Owner：A-PM（主）、A-QA（协同）
- 动作：
  1. 固化规则：`release_gate` 失败或 `open_regression_count > 0` 即 `NO_GO`，否则 `GO`。
  2. 对齐三个落点：`project_overview.release_decision`、`test_status_board.quality_gates.overall`、总控文案。
- 交付物：
  1. `output/dashboard/` 下口径一致性核对记录。
- 验收标准：
  1. 不再出现“文本 GO、门禁 NO_GO”冲突。

### PM-M2：HOLD 工作包 10 项并入统一跟踪

| PM-WP ID | 优先级 | 工作包 | Owner（主） | 最小验收标准 |
|---|---|---|---|---|
| PM-WP-01 | P0 | `wp-db-pg-canonical-model-v1.0.0` | A-ARC + A-DEV | schema 漂移检查通过，Alembic 为唯一 DDL 入口 |
| PM-WP-02 | P0 | `wp-runtime-pg-repository-switch-v1.0.0` | A-DEV | 非 `postgresql://` fail-fast，主链路回归通过 |
| PM-WP-03 | P0 | `wp-line-feedback-contract-pg-v1.0.0` | A-DEV + A-QA | contract tests 通过，可按 `workpackage_id/trace_id` 回放 |
| PM-WP-04 | P1 | `wp-trust-evidence-index-phase1-v1.0.0` | A-DEV + A-ARC | 至少 1 条全链路可回放并具审计字段 |
| PM-WP-05 | P0 | `wp-pg-only-integration-baseline-v1.0.0` | A-QA + A-DEV | PG-only 集成门禁通过，SQLite 回流可阻断 |
| PM-WP-06 | P0 | `wp-observability-phase1-run-test-sql-map-v1.0.0` | A-OBS + A-DEV | 运行态 API 契约通过，指标可追溯 |
| PM-WP-07 | P1 | `wp-dashboard-phase1-structured-rollup-v1.0.0` | A-DEV + A-QA | 空态引导、灌入后非空展示、任务下钻证据链可用 |
| PM-WP-08 | P1 | `wp-address-canonical-pg-baseline-v1.0.0` | A-DEV + A-QA | 低置信模式 Top5 非空且可复核 |
| PM-WP-09 | P1 | `wp-engineering-supervisor-phase1-audit-v1.0.0` | A-ARC + A-QA | 审计报告产出，阻断项闭环可追踪 |
| PM-WP-10 | P1 | `wp-orchestrator-phase1-crossline-closure-v1.0.0` | BM Master + A-PM | 决策包含统一判定、风险、证据、剩余阻塞 |

### PM-M3：并入后的统一执行顺序

`E3-RV-001 -> E3-RV-002 -> E3-RV-003 -> E3-RV-004 -> PM-M1 -> PM-WP-01/02/03/05/06 -> E3-RV-005 -> E3-RV-006 -> E3-RV-007`，`E3-RV-008 + PM-WP-04/07/08/09/10` 并行推进。
