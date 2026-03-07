# PRD / Architecture 测试确认报告（2026-02-27）

> 文档状态：历史归档
> 归档原因：阶段性测试确认报告，已不作为当前执行基线
> 归档日期：2026-03-06

## 1. 目的

对“最新 PRD + 最新架构 + 已回归 Story 对齐”进行一次测试回归，并输出可供 PRD 与 Architect 共同确认的证据。

## 2. 执行概览

### 2.1 全量回归（尝试）

1. 命令：`DATABASE_URL=postgresql://postgres:postgres@localhost:5432/spatial_db ./.venv/bin/python -m pytest tests/ services/ packages/ -q`
2. 日志：`output/test-reports/pytest-main-20260227-160856.log`
3. 结果：**中断（EXIT_CODE=2）**
4. 结论：全量集在 collection 阶段存在 8 个阻塞错误，当前不能作为“全仓通过”证据。

### 2.2 Story 主线回归（与当前 Epic/Story 直接相关）

1. 命令：针对 factory_agent / trust_hub / mvp acceptance / observability 相关测试集合。
2. 日志：`output/test-reports/pytest-story-main-20260227-160914.log`
3. 结果：`63 passed in 19.64s`（EXIT_CODE=0）
4. 结论：当前主线 Story 实现可用。

### 2.3 MVP 验收脚本（分 profile）

1. 日志：`output/test-reports/acceptance-profiles-20260227-160944.log`
2. 结果：
- `unit`: `all_passed=true`
- `integration`: `all_passed=true`
- `full`: `all_passed=true`
3. 产物：
- `output/acceptance/unit/address-governance-mvp-acceptance-20260227-080945.json`
- `output/acceptance/integration/address-governance-mvp-acceptance-20260227-080946.json`
- `output/acceptance/full/address-governance-mvp-acceptance-20260227-080947.json`

### 2.4 真实 LLM 门禁

1. 命令：`./.venv/bin/python scripts/run_address_governance_mvp_acceptance_real_llm_gate.py --llm-config config/llm_api.json --output-dir output/acceptance/real-gate`
2. 日志：`output/test-reports/acceptance-real-llm-gate-20260227-161000.log`
3. 结果：`all_passed=true`（EXIT_CODE=0）
4. 产物：`output/acceptance/real-gate/address-governance-mvp-acceptance-20260227-081031.json`

### 2.5 仓库卫生检查

1. 命令：`make check-repo-hygiene`
2. 日志：`output/test-reports/repo-hygiene-20260227-161045.log`
3. 结果：`[ok] no tracked venv artifacts`（EXIT_CODE=0）

## 3. 阻塞项（全量回归未通过原因）

来自 `output/test-reports/pytest-main-20260227-160856.log`：

1. `tests/test_agent_runtime.py`
- `src/runtime/orchestrator.py:40` 存在 `IndentationError`（代码语法错误）。

2. `tests/test_process_iteration_events.py`、`tests/test_router_budget_gates.py`、`tests/test_router_decision.py`、`tests/test_specialist_metadata_and_api_logs.py`、`tests/test_task_run_id_propagation.py`
- 共同阻塞：缺少 `psycopg2`（`ModuleNotFoundError`）。

3. `packages/agent_runtime/tests/test_openhands_runtime_contract.py`、`packages/agent_runtime/tests/test_runtime_selector.py`
- 共同阻塞：`packages.agent_runtime.adapters.openhands_runtime` 模块缺失（`ModuleNotFoundError`）。

## 4. 给 PRD 与 Architect 的确认结论

1. 就“当前主线 Story + MVP 验收 + 可观测性”而言：**可以确认通过**（有完整自动化证据）。
2. 就“全仓全量回归”而言：**暂不通过**，存在 8 个阻塞错误需先治理。
3. 建议 Gate 口径：
- 发布主线可按“Story 主线回归 + acceptance(full+real-llm-gate) + hygiene”判定。
- 全仓 Gate 需补齐上述 8 个阻塞项后再执行。

## 5. 建议下一步（可直接执行）

1. 修复 `src/runtime/orchestrator.py` 缩进错误并补单测。
2. 安装并锁定 `psycopg2` 依赖（建议 `psycopg2-binary` 或项目统一方案）。
3. 确认并补齐 `packages.agent_runtime.adapters.openhands_runtime`（实现或测试剔除策略）。
4. 修复后重跑全量：`tests/ services/ packages/` 并更新本报告为最终版。
