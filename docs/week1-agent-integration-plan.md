# 第一周集成计划（Agent 工程范式 × Demo 分支）

## 1. 目标

在不推翻当前 `001-system-design-spec` 分支可运行能力的前提下，完成“Contract-first + 受控工作流”最小闭环，形成可审计、可回滚、可门禁的 Agent 执行底座。

本周聚焦：

1. 冻结 6 个核心 Contract（Schema v0.1）
2. 实现最小 Orchestrator（状态机 + Evidence）
3. 复用现有 Demo 能力实现 Planner/Executor/Evaluator 适配
4. 落地最小工具契约与门禁
5. 跑通一条端到端样例任务并形成验收报告

---

## 2. 范围

### 2.1 In Scope

1. 仅 `dev` 环境执行，不触发生产变更。
2. 审批门禁先实现接口、记录和阻断逻辑。
3. Planner 先采用模板化策略，不追求复杂智能决策。
4. 复用当前 `tools/` 与 `scripts/` 资产，通过适配器接入。

### 2.2 Out of Scope

1. 多租户隔离与细粒度 RBAC 完整体系。
2. 多 Agent 并发调度优化与复杂资源编排。
3. 线上 A/B、shadow 全套灰度策略。

---

## 3. 现有资产复用映射

### 3.1 可直接复用

1. 受控执行与审批门禁雏形：`tools/factory_workflow.py`
2. Agent 角色模型：`tools/factory_agents.py`、`tools/factory_framework.py`
3. 端到端脚本入口：`scripts/factory_demo_workflow.py`、`scripts/factory_live_demo.py`
4. 最小测试与 CI：`tests/test_workflow_approvals.py`、`.github/workflows/smoke-tests.yml`

### 3.2 本周新增（不破坏现有目录）

1. `schemas/agent/*.json`（6 个 Contract）
2. `src/runtime/*`（状态机、状态存储、证据记录）
3. `src/agents/*_adapter.py`（Planner/Executor/Evaluator 适配层）
4. `src/tools/*`（Tool contract 最小实现）
5. `scripts/run_taskspec_demo.py`（统一端到端入口）

---

## 4. 本周工作分解（按天）

## D1：Contract 冻结日

### 工作内容

1. 建立 `schemas/agent/` 目录。
2. 落地 6 个 Schema：
   - `TaskSpec.json`
   - `Plan.json`
   - `ChangeSet.json`
   - `ApprovalPack.json`
   - `Evidence.json`
   - `EvalReport.json`
3. 增加 `schemas/agent/examples/` 示例文件。
4. 增加 schema 校验脚本。

### 完成标准

1. 所有示例 JSON 可通过校验。
2. Schema 版本标记为 `v0.1` 并冻结。

## D2：Runtime 状态机日

### 工作内容

1. 新建 `src/runtime/orchestrator.py`。
2. 实现状态机：
   - `SUBMITTED`
   - `PLANNED`
   - `APPROVAL_PENDING`
   - `APPROVED`
   - `CHANGESET_READY`
   - `EXECUTING`
   - `EVALUATING`
   - `COMPLETED | FAILED | ROLLED_BACK`
3. 新建 `src/runtime/state_store.py`（先用 SQLite 或内存实现）。
4. 新建 `src/runtime/evidence_store.py`。

### 完成标准

1. 状态转换路径可执行。
2. 每次状态转换都写入 Evidence。

## D3：Adapter 接入日

### 工作内容

1. 新建 `src/agents/planner_adapter.py`：输出 `Plan + ApprovalPack`。
2. 新建 `src/agents/executor_adapter.py`：只接收 `ChangeSet` 并执行。
3. 新建 `src/agents/evaluator_adapter.py`：输出 `EvalReport`。
4. 对接现有 `tools/factory_workflow.py` 能力。

### 完成标准

1. Planner/Executor/Evaluator 输入输出完全符合 Schema。
2. 缺审批自动进入 `APPROVAL_PENDING`。

## D4：工具契约与门禁日

### 工作内容

1. 新建 `src/tools/profiling_tool.py`。
2. 新建 `src/tools/ddl_tool.py`（强制 dry-run 支持）。
3. 新建 `src/tools/airflow_tool.py`（先做 DAG 生成与产物输出）。
4. 新建 `src/evaluation/gates.py`，落地最小 4 个 Gate：
   - Approval Gate
   - DDL Dry-run Gate
   - Idempotency Gate
   - Data Quality Gate

### 完成标准

1. 任一 Gate 失败会阻断执行并输出 `EvalReport=FAIL`。
2. 所有 Gate 结果可追溯到 Evidence。

## D5：端到端联调与验收日

### 工作内容

1. 新建 `scripts/run_taskspec_demo.py`。
2. 用 1 个样例 TaskSpec 跑通：
   - 规划
   - 审批
   - 生成 ChangeSet
   - 执行（dry-run）
   - 评测
   - 报告
3. 形成验收报告文档。

### 完成标准

1. 成功路径和失败路径均可复现。
2. Evidence、EvalReport、ApprovalPack 全链路齐全。

---

## 5. 门禁策略（W1 最小版）

1. Safety Gate：禁止越权操作与高风险动作。
2. Approval Gate：口径/合规/发布窗口未签收即阻断。
3. DDL Dry-run Gate：DDL 未通过 dry-run 禁止执行。
4. Idempotency Gate：所有 operation 必须有幂等键。
5. Quality Gate：关键质量规则不通过即失败。

---

## 6. 验收标准（DoD）

1. 6 个 Schema `v0.1` 冻结且通过校验。
2. 状态机全路径可跑，Evidence 全链路可追溯。
3. 审批缺失时阻断，审批完成后可继续。
4. 至少 1 条成功样例 + 1 条失败回滚样例。
5. CI 冒烟通过（schema 校验 + 单测 + 端到端 smoke）。

---

## 7. 风险与应对

1. Contract 变更频繁
- 应对：D1 冻结 `v0.1`，后续走 CR。

2. 现有 Demo 逻辑与新 Contract 不一致
- 应对：先做 Adapter 层，不直接侵入核心流程。

3. 工具层依赖外部环境导致不稳定
- 应对：先 mock + dry-run，外部集成放到 W2。

4. 评测口径分歧
- 应对：D4 锁定最小 Gate 与阈值，写入文档。

---

## 8. 下一周预告（W2）

1. 扩展 Gate 到 8 项完整清单。
2. 引入多 Agent 路由策略（Router + Specialist）。
3. 对接更真实执行底座（Airflow API / Dag 文件落地）。
4. 增加回归基线与成本阈值策略。
