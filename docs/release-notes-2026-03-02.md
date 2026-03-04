# A-TW 沉淀文档：本次发布说明（2026-03-02）

## 1. 发布概览

- 发布名称：PG-only 稳定性修复 + 文档融合对齐发布
- 发布日期：2026-03-02（Asia/Shanghai）
- 发布范围（已提交基线）：
  - `69ec7ba`（2026-03-01 18:20:08 +08:00）：收口 27 个失败项并完成 PG-only 稳定性修复
  - `e02751a`（2026-02-19 07:47:48 +08:00）：文档融合修正、废弃声明补齐、spec 对齐
- 不在本次发布范围：当前工作区未提交改动（`git status` 中的 `M/??/D`）

## 2. 架构说明

### 2.1 架构目标

本次发布聚焦两条主线：

1. 运行态主链路稳定：治理 API、治理 Worker、工厂 Agent、持久化模板、验收脚本在 PG-only 约束下统一行为。
2. 文档资产可追溯：架构、PRD、spec、kickoff 资料完成融合归档，形成一致的项目知识基线。

### 2.2 关键架构变化

- 数据库约束强化为 PG-only：
  - `scripts/run_address_governance_mvp_acceptance.py` 明确拦截非 `postgresql://` 连接。
  - 运行和验收链路统一通过 PostgreSQL 进行状态与发布记录读写。
- 治理 API 路由链路收敛：
  - `services/governance_api/app/main.py` 统一挂载 `tasks/reviews/rulesets/ops/observability/lab/manual-review`。
  - 可观测与治理数据通过同一 API 边界暴露，减少跨模块口径漂移。
- 工具生成与持久化模板同步：
  - `tools/factory_workflow.py`、`tools/generated_tools/persisters/db_persister.py`、`tools/process_compiler/tool_templates/persisters.py` 同步更新，避免模板与运行态脱节。
- 文档融合资产归档：
  - `.trae/documents/*` 与 `.trae/specs/*` 新增/修订，覆盖架构、设计、计划、diagram、kickoff 资料。

## 3. 运行手册

### 3.1 环境准备

```bash
# 1) 启动依赖（PostgreSQL + Redis）
make up

# 2) 安装依赖（如首次）
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3.2 核心验证流程

```bash
# 集成测试（仓库既有入口）
make test-integration

# 地址治理 MVP 验收（PG-only）
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/spatial_db \
  .venv/bin/python scripts/run_address_governance_mvp_acceptance.py \
  --output-dir output/acceptance

# 可观测 + PG 基础能力验收
.venv/bin/python scripts/run_observability_pg_foundation_acceptance.py \
  --output-dir output/acceptance
```

### 3.3 服务启动（本地联调）

```bash
# Governance API
.venv/bin/python -m uvicorn services.governance_api.app.main:app --host 127.0.0.1 --port 8000

# Trust Data Hub API
.venv/bin/python -m uvicorn services.trust_data_hub.app.main:app --host 127.0.0.1 --port 8001
```

### 3.4 发布前检查清单

- `DATABASE_URL` 必须为 `postgresql://` 协议。
- `make test-integration` 通过。
- 两份验收报告已生成到 `output/acceptance/`。
- 与本次发布相关的 Linear Issue 已创建并与 PR 关联（项目强制规则）。

## 4. 变更记录

### 4.1 Commit 级摘要

| Commit | 时间（+08:00） | 类型 | 说明 |
| --- | --- | --- | --- |
| `69ec7ba` | 2026-03-01 18:20:08 | Fix | 收口 27 个失败项，完成 PG-only 稳定性修复；覆盖 API、Worker、Agent、验收与测试链路 |
| `e02751a` | 2026-02-19 07:47:48 | Docs | 文档融合修订，补齐废弃声明与 spec 对齐，沉淀架构与 kickoff 资料 |

### 4.2 本次重点文件（节选）

- 运行态代码：
  - `services/governance_api/app/routers/{lab,observability,rulesets}.py`
  - `services/governance_worker/app/jobs/result_persist_job.py`
  - `packages/factory_agent/{agent,llm_gateway}.py`
  - `database/agent_runtime_store.py`
- 测试与验收：
  - `tests/test_mvp_acceptance_script.py`
  - `tests/test_observability_foundation_acceptance_script.py`
  - `services/governance_api/tests/test_runtime_workpackage_pipeline_stability.py`
- 文档融合：
  - `.trae/documents/*`
  - `.trae/specs/*`

## 5. 风险与回滚说明

- 已知风险：本地仍存在未提交改动，若直接打包可能引入未审查内容。
- 回滚建议：按 commit 回滚到 `69ec7ba`（功能稳定基线）或更早稳定点，并重新执行第 3 节验收流程。
- 追踪要求：所有回滚与补丁动作需在 Linear 中记录并与 PR 关联。

## 6. 文档用途声明（A-TW）

- 架构说明：用于统一发布窗口内的技术边界与关键决策。
- 运行手册：用于发布执行、环境核验、故障排查入口。
- 变更记录：用于审计追溯、跨团队同步与验收签收。
