# 第一周任务清单（Todo）

## P0（必须完成）

1. [x] 建立 `schemas/agent` 目录并新增 6 个 Schema 文件。
2. [x] 新增 `schemas/agent/examples` 示例 JSON。
3. [x] 新增 Schema 校验脚本（可本地一键执行）。
4. [x] 新建 `src/runtime/orchestrator.py` 并实现状态机。
5. [x] 新建 `src/runtime/state_store.py`。
6. [x] 新建 `src/runtime/evidence_store.py`。
7. [x] 状态迁移全量写 Evidence。
8. [x] 接入审批门禁（未审批阻断）。

## P1（本周应完成）

1. [x] 新建 `src/agents/planner_adapter.py`（输出 Plan + ApprovalPack）。
2. [x] 新建 `src/agents/executor_adapter.py`（消费 ChangeSet）。
3. [x] 新建 `src/agents/evaluator_adapter.py`（输出 EvalReport）。
4. [x] 新建 `src/tools/profiling_tool.py`。
5. [x] 新建 `src/tools/ddl_tool.py`（含 dry-run）。
6. [x] 新建 `src/tools/airflow_tool.py`（先 DAG 生成）。
7. [x] 新建 `src/evaluation/gates.py`。
8. [x] 落地 4 个最小 Gate：Approval / DDL dry-run / Idempotency / Quality。
9. [x] 新建 `scripts/run_taskspec_demo.py` 作为统一 E2E 入口。
10. [x] 新增单测：
   - [x] 缺审批阻断
   - [x] 审批后执行通过
   - [x] Gate fail 阻断
11. [x] 更新 CI workflow：加入 schema 校验与 e2e smoke。

## P2（可顺延）

1. [x] 输出 `docs/week1-acceptance-report.md`。
2. [x] 整理 W2 backlog（多 Agent 路由与真实工具接入）。  
   - 产出：`docs/week2-backlog-2026-02-14.md`
3. [x] 增加更多评测样例（性能、成本、回归）。  
   - 产出：`docs/evaluation-samples-expansion-plan-2026-02-14.md`

---

## 每日检查点

### D1 结束检查

1. [x] 6 个 Schema 完成并通过校验
2. [x] 评审后冻结 v0.1

### D2 结束检查

1. [x] 状态机跑通
2. [x] Evidence 连续写入可追溯

### D3 结束检查

1. [x] 3 个 adapter 可联通
2. [x] ApprovalPending 分支生效

### D4 结束检查

1. [x] 3 个工具契约可调用
2. [x] 4 个 Gate 生效并输出 EvalReport

### D5 结束检查

1. [x] 成功链路 e2e 跑通
2. [x] 失败链路 e2e 可复现
3. [x] CI 冒烟已配置（本地通过）

---

## 交付验收（DoD）

1. [x] Schema v0.1 冻结并可校验
2. [x] Orchestrator 状态机可执行
3. [x] 审批门禁阻断/放行行为正确
4. [x] Evidence + EvalReport + ApprovalPack 完整
5. [x] 本地与 CI 冒烟均通过
