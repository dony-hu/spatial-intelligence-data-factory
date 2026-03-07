# MVP PRD 评审与整改清单（2026-02-27）

> 文档状态：历史归档
> 归档原因：阶段性评审与整改清单，已被后续 Epic / Story / Acceptance 收敛替代
> 归档日期：2026-03-06

## 1. 评审范围

- PRD：`archive/docs/formal/product/prd-2026-02-27.md`
- Epic：`docs/epics/address-governance-mvp/epic.md`
- Stories：`docs/stories/MVP-A1` ~ `MVP-A6`
- 代码基线：`packages/factory_agent`、`packages/factory_cli`、`packages/trust_hub`、`services/governance_api`

## 2. 总体结论

当前实现已完成 P0/P1 关键整改并具备最新实测证据，结论为：**MVP 阶段性通过（Conditional Pass）**。

核心偏差：

1. 验收脚本 A1/A2 判定语义偏移（与 Story 定义不一致）。
2. Dry-run 仅静态回包，未真实执行入口。
3. 发布后执行链路与 Runtime 运行结果未闭环。
4. Trust Hub 主持久化链路仍以本地文件为主，未完全收敛到数据库主路径。

## 3. 分级问题清单

### P0（必须先完成）

1. A1/A2 验收判定与 Story 语义对齐。
- 要求：A1 必须验证 CLI-Agent-LLM 需求确认；A2 必须验证 dry-run 真实执行。
- 结果：已开始修复（本次提交已落地）。

2. Dry-run 必须执行入口并对失败 fail-fast。
- 要求：执行 `entrypoint.sh/entrypoint.py`，失败返回 `blocked` + 原因 + 证据。
- 结果：已开始修复（本次提交已落地）。

### P1（本 Epic 内完成）

1. CLI 命令流补齐。
- 现状：`scripts/factory_cli.py` 缺少明确 `dryrun/publish` 子命令，`run-skill` 未实现。
- 目标：最小闭环命令集应直接覆盖 A1/A2/A3。

2. 发布后执行与结果回传。
- 现状：发布仅写 evidence + 入库；未触发 runtime 执行。
- 目标：发布后可触发一次执行并返回运行结果摘要。

3. Trust Hub 数据闭环主路径统一。
- 现状：能力与样例主写入 `data/trust_hub.json`。
- 目标：数据库为主、文件为可选缓存；查询链路与治理库一致。

4. 真实 LLM 验收门禁。
- 现状：单测中大量 monkeypatch LLM 调用。
- 目标：增加“真实 LLM 环境专用验收任务”，无配置时 fail-fast。

### P2（后续优化）

1. 产物路径规范化与静态暴露边界收紧。
2. Story 验收脚本拆分（单元验收 / 集成验收 / 真实外部依赖验收）。

## 4. 整改计划（A1~A6 映射）

1. A1：新增真实 LLM 验收门禁（独立 job，默认不 mock）。
2. A2：dry-run 真执行 + 失败阻塞审计（已完成第一版）。
3. A3：发布后执行回路（publish -> trigger -> result summary）。
4. A4：流水线最小执行报告与可观测指标对齐。
5. A5：Trust Hub DB 主路径改造（capability/sample upsert & query）。
6. A6：DB 一致性收口（governance/runtime/trust 查询链路统一）。

## 5. 本轮已完成修复

1. `scripts/run_address_governance_mvp_acceptance.py`
- 新增 A1 真正的 requirement 对话检查。
- 新增 A2 真正的 dry-run 检查。
- `all_passed` 由 A1~A6 全量关键项共同决定。
- 引入 `MVP_ACCEPTANCE_MOCK_LLM=1` 仅用于测试环境可重复执行；默认保持严格模式。
- 新增 `A1_llm_real_service_gate` 门禁检查，默认要求真实 LLM 配置可用（无配置直接阻塞并 fail-fast）。
- 新增 `--llm-config` 参数，支持显式指定真实 LLM 配置路径。

2. `packages/factory_agent/agent.py`
- `dryrun_workpackage` 改为真实执行 `entrypoint.sh/entrypoint.py`。
- 执行失败返回 `blocked` + `dryrun_execution_failed`。
- 产出 `observability/dryrun_report.json` 作为执行证据。

3. 测试补齐
- `tests/test_factory_agent_dryrun_no_fallback.py` 新增 dry-run 执行失败阻塞用例。
- `tests/test_mvp_acceptance_script.py` 新增 A1/A2 验收项断言。
- `tests/test_mvp_acceptance_script.py` 新增“真实 LLM 门禁缺失配置即失败”用例。

## 6. 当前状态

- P0-1：已完成。
- P0-2：已完成。
- P1-1（CLI 命令流补齐）：已完成。
- P1-2（发布后执行与结果回传）：已完成。
- P1-3（Trust Hub DB 主路径）：已完成（capability/sample 主路径入库）。
- P1-4（真实 LLM 验收门禁）：已完成。
- P2：待继续推进。

## 7. 最新验收证据（真实 LLM 模式）

- 运行时间（UTC）：`2026-02-27T06:47:06+00:00`
- 报告 JSON：`output/acceptance/address-governance-mvp-acceptance-20260227-064706.json`
- 报告 Markdown：`output/acceptance/address-governance-mvp-acceptance-20260227-064706.md`
- 关键结论：
1. `all_passed=true`
2. `A1_llm_real_service_gate.passed=true`
3. `A1_cli_agent_llm_interaction.passed=true`

## 8. P0 重构推进（环境治理 + 验收链路拆分）

1. 环境治理（Git 噪音控制）
- `.gitignore` 已补充：`.venv.broken.*/`、`output/acceptance/`、`output/logs/`。
- 目标：避免本地解释器重建与验收产物污染业务提交。

2. 验收链路拆分（可独立门禁）
- 主脚本 `scripts/run_address_governance_mvp_acceptance.py` 新增 `--profile`：
  - `full`：全量 A1~A6
  - `unit`：A1 对话 + A2 dryrun
  - `integration`：A3~A6 发布/查询/审计/持久化
  - `real-llm-gate`：真实 LLM 门禁（A1_llm_real_service_gate + A1 对话）
- 新增拆分入口脚本：
  - `scripts/run_address_governance_mvp_acceptance_unit.py`
  - `scripts/run_address_governance_mvp_acceptance_integration.py`
  - `scripts/run_address_governance_mvp_acceptance_real_llm_gate.py`

3. 自动化测试补齐
- `tests/test_mvp_acceptance_pipeline_split.py`
- `tests/test_repo_hygiene_gitignore.py`

## 9. P1 重构推进（Agent 编排解耦-第一步）

1. 路由能力从 `FactoryAgent` 内联条件分支中抽离，新增：
- `packages/factory_agent/routing.py`
- `detect_agent_intent(prompt)` 返回标准意图：
  - `store_api_key/list_workpackages/query_workpackage/dryrun_workpackage/publish_workpackage/list_sources/generate_workpackage/confirm_requirement`

2. `FactoryAgent.converse` 改为“意图识别 + handler 分发”，行为与原逻辑保持一致。

3. 测试补齐：
- `tests/test_factory_agent_routing.py`
  - 意图识别矩阵测试（中英文关键词）
  - `converse` 分发语义测试

4. LLM 基础设施解耦（第二步）
- 新增 `packages/factory_agent/llm_gateway.py`，封装 `load_config/run_requirement_query` 调用。
- `FactoryAgent._run_requirement_query` 已改为委托 gateway，减少 Agent 与外部 LLM SDK/配置的直接耦合。
- 新增测试：`tests/test_factory_agent_llm_gateway.py`。

5. 发布与审计编排解耦（第三步）
- 新增 `packages/factory_agent/publish_workflow.py`：
  - 封装工作包发布校验、evidence 写入、执行结果分支、blocked 审计回调。
- `FactoryAgent._handle_publish_workpackage` 已改为委托 `WorkpackagePublishWorkflow.run(...)`。
- `FactoryAgent` 增加 `_log_publish_blocked_event` 作为审计回调适配点。
- 新增测试：`tests/test_factory_agent_publish_workflow.py`（覆盖 `blocked+audit` 与 `published` 主路径）。

6. Dry-run 编排解耦（第四步）
- 新增 `packages/factory_agent/dryrun_workflow.py`：
  - 封装 dry-run 的工作包契约校验、执行调用与阻塞语义。
- `FactoryAgent._handle_dryrun_workpackage` 已改为委托 `WorkpackageDryrunWorkflow.run(...)`。
- 新增测试：`tests/test_factory_agent_dryrun_workflow.py`（覆盖 `workpackage_not_found` 与 `success` 主路径）。

## 10. 评审问题修复状态（2026-02-27 更新）

1. 已修复：验收 profile 执行隔离不彻底
- 修复点：`scripts/run_address_governance_mvp_acceptance.py`
  - `run_acceptance(..., profile=...)` 现在按 profile 真正裁剪执行步骤。
  - 未执行检查项统一打 `skipped=true`（非 required 不计入失败）。
- 新增回归用例：
  - `tests/test_mvp_acceptance_pipeline_split.py::test_mvp_acceptance_integration_script_isolated_from_llm_gate`
- 证据：
  - `output/acceptance/integration-isolated/address-governance-mvp-acceptance-20260227-074538.json`
  - 在 `MVP_ACCEPTANCE_MOCK_LLM=0` 且 `--llm-config config/not_exists.json` 下，`profile=integration` 仍 `all_passed=true`。

2. 已修复：PRD 评审结论与证据不一致
- 修复点：本文件“总体结论”已更新为“阶段性通过（Conditional Pass）”。

3. 已启动：`.venv` 专项治理
- 动作：
  - `git rm -r --cached .venv`，取消 `.venv` 全量跟踪（不删除本地文件）。
  - 新增仓库卫生检查脚本：`scripts/check_repo_hygiene.sh`。
  - 新增 Make 入口：`make check-repo-hygiene`。
- 验证：
  - `./scripts/check_repo_hygiene.sh` 返回 `[ok] no tracked venv artifacts`。
