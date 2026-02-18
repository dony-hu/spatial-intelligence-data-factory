# W2 Backlog（多 Agent 路由与真实工具接入）

日期：2026-02-14  
范围：`spatial-intelligence-data-factory`（平台仓）

## 1. 目标

1. 将单 Agent 串行执行升级为 Router + Specialist 的受控协同。
2. 将关键外部工具从占位调用推进到真实接入（含降级与观测）。
3. 将执行结果统一纳入事件链路（版本、回滚、失败回放证据）。

## 2. P0 Backlog（本周必须推进）

| ID | 事项 | 负责人角色 | 依赖 | 交付物 | 验收标准 |
|---|---|---|---|---|---|
| W2-R1 | Router 策略落地（按任务类型/风险/成本路由） | Dev | 无 | `tools/agent_server.py` 路由策略 + 策略说明文档 | 同一输入可复现稳定路由结果 |
| W2-R2 | Specialist 注册（process_expert/planner/executor/evaluator）统一元数据 | Dev | W2-R1 | tool registry 元数据字段扩展 | 查询接口可返回 agent 能力、版本、健康状态 |
| W2-T1 | 真实工具接入第一批（map_service/web_search/review_platform） | Dev | W2-R1 | 最小真实调用 + fallback | 任一工具失败时不阻断主流程且有错误码 |
| W2-T2 | 外部工具调用审计链（请求、响应、耗时、错误） | Dev | W2-T1 | `api_call_log` 查询接口 | 可按 `task_run_id` 回放外部调用轨迹 |
| W2-G1 | 路由+工具的门禁规则（成本上限/超时上限/重试策略） | Dev/QA | W2-T2 | gate 规则扩展与测试 | 超预算或超时触发 FAIL 且错误码明确 |

### P0 执行状态（更新于 2026-02-14）

1. `W2-R1`：已完成（已落地路由决策函数/API，并接入 `process_console` 可视化）。
2. `W2-T1`：已完成（已落地真实调用+降级，执行链已接入验证编排器）。
3. `W2-R2`：已完成（已新增专家元数据接口并接入控制台展示）。
4. `W2-T2`：已完成（已新增 `api_call_log` 查询接口并打通 `task_run_id` 维度联调）。
5. `W2-G1`：已完成（已落地 `max_steps`/成本/超时门禁，并支持 `settings/router_gates.json` + 环境变量阈值覆盖）。

## 3. P1 Backlog（本周应完成）

| ID | 事项 | 负责人角色 | 依赖 | 交付物 | 验收标准 |
|---|---|---|---|---|---|
| W2-O1 | Router 决策可视化（控制台展示） | FE/Dev | W2-R1 | 控制台路由详情面板 | 可按 task 查看选路原因 |
| W2-O2 | 回放工具链整合（失败队列 -> replay -> process iteration） | Dev | W2-T2 | 自动回传脚本与接口 | 回放结果与迭代事件可关联 |
| W2-C1 | 变更兼容检查（旧版本流程可运行） | QA/Dev | W2-R2 | 回归报告 | 历史版本至少 1 个样例可跑通 |

## 4. 排期建议（5 天）

1. D1-D2：W2-R1, W2-R2  
2. D2-D3：W2-T1, W2-T2  
3. D4：W2-G1  
4. D5：W2-O1, W2-O2, W2-C1（至少完成一项）

## 5. 风险与应对

1. 外部 API 不稳定导致波动。  
应对：统一 fallback + 熔断 + 缓存。

2. 多 Agent 路由难复现。  
应对：路由输入与决策写入 evidence，支持重放。

3. 成本不可控。  
应对：强制成本/时延 gate，超限降级到基础路径。
