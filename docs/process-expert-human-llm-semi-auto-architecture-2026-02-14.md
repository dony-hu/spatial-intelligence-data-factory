# 工艺专家架构重构方案（人工 + LLM 半自动）

## 1. 决策背景

- 原方案：工艺Agent基于测试用例自举、多轮迭代、达到阈值后尝试闭环推进。
- 新方案：人工作为决策主体，LLM作为草案/修订建议生成器，写操作必须显式确认。

## 2. 目标与边界

### 目标
- 保留 LLM 在工艺草案生成与改进建议上的效率优势。
- 将“是否修改、是否发布、风险接受”全部收敛到人工决策。
- 降低自举迭代引入的不可控漂移和误发布风险。

### 非目标
- 不再追求无人值守自动迭代升版。
- 不在脚本中自动确认发布。

## 3. 新流程（SOP）

1. 输入需求，调用 `action=design` 生成草案。
2. 系统生成 `human_decision_template.json`，人工完成评审结论。
3. 若人工要求修订，将 `change_request` 回填并触发一次增量修改。
4. 若涉及写操作，进入 `pending_confirmation`。
5. 人工通过 `/api/v1/confirmation/respond` 明确确认或拒绝。

## 4. 代码落地

- 新增：`tools/process_expert_human_loop.py`
  - `ProcessExpertHumanLoopRunner`
  - 输出 `design_result.json`、`human_decision_template.json`、`final_summary.json`
  - 可选读取人工 `decision_payload` 执行一次 `modify_process`

- 调整：`scripts/run_process_expert_human_loop.py`
  - 从“自举多轮Runner”改为“半自动人机协同Runner”入口
  - 支持 `--decision-file` 人工回放

- 调整：`scripts/run_process_expert_closed_loop.sh`
  - 停止自动确认写操作
  - 改为输出人工执行确认命令

- 调整：`tools/agent_server.py`
  - `action=design` 响应增加：
    - `mode=human_llm_semi_auto`
    - `requires_human_decision=true`
    - `publish_strategy=confirmation_gate_required`
  - 非法 action 统一返回标准错误

## 5. 风险与控制

- 风险：人工步骤增多导致时延上升。
  - 控制：保留脚本化模板与标准评审字段，降低人工成本。
- 风险：历史脚本仍按闭环自动认知执行。
  - 控制：脚本输出明确“人工动作 required”。

## 6. 验收标准

- 能生成工艺草案与人工决策模板。
- 不存在脚本自动确认发布行为。
- 无旧自动迭代动作入口。
- 测试覆盖“有/无人工决策文件”两条路径。
