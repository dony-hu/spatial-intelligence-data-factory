# PRD进展报告（MVP + 可观测性）- 2026-02-27

> 文档状态：历史归档
> 归档原因：阶段性进展报告，现由 Epic / Story / Acceptance 文档承接
> 归档日期：2026-03-06

## 1. 评审范围

1. PRD：`archive/docs/formal/product/prd-2026-02-27.md`
2. MVP Epic：`docs/epics/address-governance-mvp/epic.md`
3. 可观测性架构：`docs/architecture/系统可观测性能力设计.md`
4. 代码范围：`packages/factory_agent`、`packages/trust_hub`、`services/governance_api`、`scripts/*acceptance*`

## 2. 总体结论

当前主线已具备“功能可跑通 + 测试可验证 + 可观测可查看”的阶段能力，结论为：**阶段性通过**。  
其中 MVP A1~A6 在最新 `full` 验收中全通过；可观测性接口、页面与流式事件链路测试通过。

## 3. 功能进展（对照 MVP A1~A6）

1. A1 CLI-Agent-LLM 需求确认：已完成
- 真实 LLM 门禁存在，`A1_llm_real_service_gate` 与 `A1_cli_agent_llm_interaction` 均通过。

2. A2 治理 dry-run：已完成
- dry-run 走真实入口执行，失败返回 `blocked`，并产出 `observability/dryrun_report.json`。

3. A3 工作包发布到 Runtime：已完成
- 发布后触发执行并回传结果；失败路径阻塞并审计。

4. A4 流水线最小构建：已完成（MVP标准）
- 通过 API 查询与 compare 能返回稳定结果；流程证据可回查。

5. A5 Trust Hub 能力沉淀：已完成（MVP标准）
- 能力/样例主路径已入库并可查询，覆盖 no-fallback 基本约束。

6. A6 DB 持久化闭环：已完成（MVP标准）
- 发布记录、审计事件、查询链路可在数据库侧验证。

## 4. 可观测性进展（PRD EPIC C 对齐）

1. 快照与流式接口可用
- `GET /v1/governance/lab/observability/snapshot`
- `GET /v1/governance/lab/observability/stream`

2. 可观测页面可用
- `GET /v1/governance/lab/observability/view?env=dev|staging`
- 页面核心区块与连接状态更新均有测试覆盖。

3. 运行态事件可见
- 任务生命周期、审计事件、规则发布阻塞事件可在 snapshot/events 中看到。

4. 观测相关测试通过
- API/集成/E2E（单测级）均通过（见第 5 节）。

## 5. 最新测试与验收证据

### 5.1 自动化测试执行（本次实测）

1. 功能主线回归：
- 命令：聚合执行 `factory_agent + trust_hub + cli + publish api/e2e/repository + mvp acceptance tests`
- 结果：`48 passed`

2. 可观测性回归：
- 命令：`services/governance_api/tests/test_lab_api.py`
  `services/governance_api/tests/test_observability_integration.py`
  `tests/test_observability_integration_e2e.py`
  `tests/web_e2e/test_observability_live_ui.py`
- 结果：`32 passed, 1 skipped`

### 5.2 验收脚本产物（本次实测）

1. MVP full：
- `output/acceptance/address-governance-mvp-acceptance-20260227-073733.json`
- `output/acceptance/address-governance-mvp-acceptance-20260227-073733.md`
- 关键结论：`profile=full`，`all_passed=true`，A1~A6 全通过。

2. MVP integration：
- `output/acceptance/address-governance-mvp-acceptance-20260227-073707.json`
- 关键结论：`profile=integration`，`all_passed=true`。

3. MVP unit：
- `output/acceptance/unit/address-governance-mvp-acceptance-20260227-073753.json`
- 关键结论：`profile=unit`，`all_passed=true`。

4. MVP real-llm-gate：
- `output/acceptance/real-gate/address-governance-mvp-acceptance-20260227-073830.json`
- 关键结论：`profile=real-llm-gate`，`all_passed=true`。

## 6. 架构与测试观察（需跟进）

1. `profile` 执行隔离已修复（P1 已关闭）
- 现状：`scripts/run_address_governance_mvp_acceptance.py` 已按 profile 裁剪执行步骤，未执行项标记 `skipped`。
- 证据：`output/acceptance/integration-isolated/address-governance-mvp-acceptance-20260227-074538.json`

2. 文档结论历史残留已修复（P1 已关闭）
- `archive/docs/reviews/prd-review-address-governance-mvp-2026-02-27.md` 总体结论已更新为“阶段性通过（Conditional Pass）”。

3. `.venv` 专项治理已启动（P2 持续）
- 已执行 `git rm -r --cached .venv`，并新增 `scripts/check_repo_hygiene.sh` + `make check-repo-hygiene`。
- 当前脚本校验结果：`[ok] no tracked venv artifacts`。

## 7. 下一步建议（BMAD）

1. 修复验收 profile 的“执行隔离”实现（而非仅判定隔离）。
2. 同步更新 PRD 评审文档结论为“阶段性通过/有条件通过”并附最新证据时间戳。
3. 执行一次仓库卫生专项（`.venv` 追踪清理策略）并固化到工程规范与CI检查。
