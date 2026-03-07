# lane-06 baseline 与统一验证入口

## 1. 目的

本文件用于把 Epic13 启动期 `lane-06 QA / 集成门禁` 的最小 baseline、统一验证入口和当前已知阻塞项固化下来。

它服务三个直接目标：

1. 让 `lane-06` 在并行开发早期先给出一套最小 smoke 基线，而不是等所有 Lane 开工后再临时拼回归命令。
2. 让 `PAR-S4` 中定义的“集成值班 / gate / 合并窗口”有具体可执行入口。
3. 让后续 `PAR-S5` 可以直接复用统一的 gate 字段和验证命令。

## 2. 当前绑定关系

| 项 | 当前值 |
| --- | --- |
| owner | `lane-06 QA / 集成门禁` |
| branch | `codex/lane-06-qa-integration` |
| worktree | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/06-qa-integration` |
| 适用阶段 | Epic13 启动期 / `48h contract sprint` |
| 消费方 | 集成值班位、`PAR-S4`、`PAR-S5`、各 Lane PR 作者 |

## 3. baseline 分层

### 3.1 P0 启动层

这层只回答“仓库卫生和基础契约守卫是否还能跑”。

1. 仓库卫生检查
   - 命令：`./scripts/check_repo_hygiene.sh`
   - 目的：确认 `.venv` 产物未被跟踪、主线目录不存在 local-file-db 运行时引用。
2. 工作包清理守卫
   - 命令：`./scripts/check_workpackage_cleanup.sh`
   - 目的：守住 workpackage v1 清理、schema versioning、样例和 companion artifacts。

### 3.2 P1 核心回归层

这层用于回答“Runtime / API 共享主链路是否还能通过最小契约回归”。

1. Runtime 核心契约回归
   - 入口参考：`scripts/run_epic3_core_acceptance.py`
   - 最小命令组：
     - `PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py`
     - `PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_events_api_contract.py`
     - `PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_llm_interactions_api_contract.py`
     - `PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_observability_rbac.py`
     - `PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_upload_batch.py`
2. 最小真实链路
   - 命令：`./scripts/run_governance_e2e_minimal.sh`
   - 目的：在真实运行态入口上验证最小治理链路，而不是只停留在纯单测。

### 3.3 P2 扩展回归层

这层用于回答“完整集成与 Web E2E 是否具备进入集成窗口的条件”。

1. Web E2E 最小入口
   - 命令：`./scripts/run_web_e2e.sh tests/web_e2e/test_runtime_observability_workpackage_search_ui.py`
2. Web E2E 目录回归
   - 命令：`PYTHONPATH=. .venv/bin/python scripts/run_web_e2e_catalog.py`
3. 全量集成回归
   - 命令：`make test-integration`
4. 夜间质量门禁
   - 命令：`.venv/bin/python scripts/run_nightly_quality_gate.py`

## 4. 统一 gate 结论口径

`lane-06` 在集成窗口里只输出三类结论：

1. `PASS`
   - 前置 smoke / 回归通过，可进入合并窗口。
2. `BLOCKED`
   - 环境依赖、测试环境、本地 worktree 状态或共享契约前置未闭环，当前不允许进入合并窗口。
3. `NEEDS-FIX`
   - 已进入验证，但回归失败，必须回到原始 Lane / Worktree 修复后重跑。

禁止使用“先合进去再补测”替代上述 gate 结论。

## 5. 环境依赖基线

进入 `lane-06` gate 前，至少准备好：

1. worktree 本地 `.venv`
   - 当前 `codex/lane-06-qa-integration` 尚未初始化 `.venv`
2. PostgreSQL
   - 推荐 `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/spatial_db`
3. No-Fallback 相关环境
   - `TRUST_ALLOW_MEMORY_FALLBACK=0`
   - `GOVERNANCE_ALLOW_MEMORY_FALLBACK=0`
4. 真实 LLM 配置
   - `LLM_CONFIG_PATH` 或默认 `config/llm_api.json`
5. Web E2E 依赖
   - `requirements-web-e2e.txt`
   - `python -m playwright install chromium`
   - 如不本地拉起 API，则提供 `WEB_E2E_BASE_URL`

## 6. 当前已知阻塞与探测结果（2026-03-07）

| 项 | 结论 | 依据 |
| --- | --- | --- |
| 仓库卫生检查 | `PASS` | 已在 `codex/lane-06-qa-integration` worktree 执行 `./scripts/check_repo_hygiene.sh`，结果通过。 |
| 工作包清理守卫 | `BLOCKED` | 已执行 `./scripts/check_workpackage_cleanup.sh`，失败原因为 `pytest: command not found`。 |
| worktree 本地 Python 环境 | `BLOCKED` | 当前 worktree 下不存在 `.venv/bin/python` 与 `.venv/bin/pytest`。 |
| 最小真实链路 | `FOLLOW-UP` | 命令已确认存在，但需本地 `.venv`、PostgreSQL、LLM 配置共同就绪后再跑。 |
| Web E2E 最小入口 | `FOLLOW-UP` | 命令已确认存在，但需 Playwright Chromium 与 API 入口就绪后再跑。 |
| `W-STW` 自动 TEA 步骤 | `FOLLOW-UP` | 当前未安装 `bmad-tea-testarch-atdd` / `bmad-tea-testarch-trace`。 |
| Linear 绑定 | `FOLLOW-UP` | 当前无本地 Linear 接入能力。 |

## 7. 各 Lane 进入集成窗口前必须提供的输入

各 Lane 在把 PR 交给 `lane-06` 前，至少提供：

1. PR 描述中的 owned surface
2. 影响的共享契约列表
3. 本 Lane 最小测试集或人工检查单
4. 需要重点回归的下游 Lane
5. 如触及红区对象，相关 owner 审核结论

缺任一项时，`lane-06` 可直接判定 `BLOCKED`。

## 8. 推荐执行顺序

启动期建议按下面顺序运行：

1. `./scripts/check_repo_hygiene.sh`
2. `./scripts/check_workpackage_cleanup.sh`
3. Runtime 核心契约回归最小命令组
4. `./scripts/run_governance_e2e_minimal.sh`
5. `./scripts/run_web_e2e.sh tests/web_e2e/test_runtime_observability_workpackage_search_ui.py`

若第 1-2 步未通过，不建议继续执行更重的 P1 / P2 验证。

## 9. 下游消费说明

1. `PAR-S4` 应直接消费这里的 `PASS / BLOCKED / NEEDS-FIX` 结论口径。
2. `PAR-S5` 应直接消费这里的“Lane 进入集成窗口前必填字段”。
3. 集成值班位应直接消费这里的“当前已知阻塞与探测结果”决定是否开放合并窗口。
