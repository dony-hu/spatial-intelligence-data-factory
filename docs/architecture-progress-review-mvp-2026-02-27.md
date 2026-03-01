# 架构进展审视报告（MVP）- 2026-02-27

## 1. 审视结论

当前代码从“可运行”已进入“可重构”阶段，P0 与 P1 的关键改造已连续落地并通过回归。  
结论：**阶段性通过（此前 2 个结构问题已完成修复/治理启动）**。

## 2. 关键发现（按严重级）

### P1-1 验收脚本 profile 执行隔离（已修复）

- 修复位置：`scripts/run_address_governance_mvp_acceptance.py`
- 修复结果：
1. `run_acceptance(..., profile=...)` 按 profile 裁剪执行步骤。
2. 未执行检查项统一标记 `skipped=true`。
3. `integration` 已可在 `MVP_ACCEPTANCE_MOCK_LLM=0` 且无可用 LLM 配置时独立通过。

### P2-1 Agent 内存在重构遗留死代码（待优化）

- 位置：`packages/factory_agent/agent.py:319-348`
- 问题：`_build_publish_blocked` 在发布逻辑迁移到 `publish_workflow` 后不再被调用。
- 影响：增加维护噪音，易误导后续改造者继续在旧路径上追加逻辑。
- 建议：删除死代码或明确标注 deprecated 并在下个迭代移除。

## 3. 本阶段进展（已完成）

1. 验收门禁与链路
- 主验收脚本增加真实 LLM 门禁与 `--profile` 能力。
- 新增拆分入口脚本：`unit/integration/real-llm-gate`。

2. Agent 编排解耦（连续四步）
- 对话路由抽离：`packages/factory_agent/routing.py`
- LLM 调用抽离：`packages/factory_agent/llm_gateway.py`
- 发布编排抽离：`packages/factory_agent/publish_workflow.py`
- Dry-run 编排抽离：`packages/factory_agent/dryrun_workflow.py`

3. 工程卫生
- `.gitignore` 补齐 `.venv.broken.*/` 与验收产物目录。

4. 测试资产补齐
- 新增组件/链路测试：
  - `tests/test_mvp_acceptance_pipeline_split.py`
  - `tests/test_repo_hygiene_gitignore.py`
  - `tests/test_factory_agent_routing.py`
  - `tests/test_factory_agent_llm_gateway.py`
  - `tests/test_factory_agent_publish_workflow.py`
  - `tests/test_factory_agent_dryrun_workflow.py`

## 4. 架构收益评估

1. 可替换性提升
- LLM 与发布/dry-run 执行已具备组件边界，可独立演进与测试。

2. 变更风险下降
- Agent 主类职责缩小，新增能力优先在 workflow/gateway 层扩展。

3. 验证能力增强
- 从“端到端单脚本”进化为“可分层执行 + 可组合门禁”。

## 5. 下一步建议（架构师）

1. 优先修复 `profile` 执行隔离（P1）。
2. 清理 `agent.py` 死代码与重复辅助函数（P2）。
3. 在 `FactoryAgent` 引入统一 `WorkflowContext`（路径、repo、时钟、审计器）以减少回调参数散落。
4. 将验收报告 schema 固化为版本化契约（例如 `acceptance_schema_version`），避免后续脚本扩展破坏兼容。

## 6. 进入下一阶段门槛

满足以下条件即可进入 P2 及后续功能扩展：

1. 移除或标注所有已迁移旧路径（含 `_build_publish_blocked`）。
2. `.venv` 专项治理纳入 CI pre-check（`make check-repo-hygiene`）。
3. 关键回归集保持全绿。
