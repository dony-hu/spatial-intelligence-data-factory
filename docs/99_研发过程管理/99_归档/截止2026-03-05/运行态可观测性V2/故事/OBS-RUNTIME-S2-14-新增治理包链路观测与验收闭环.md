# Story：OBS-RUNTIME-S2-14 新增治理包链路观测与验收闭环

## 1. 目标

交付“新增治理包”运行态观测能力，能够在可观测页面完整观测并下钻以下链路：

1. `user/test_client -> factory_cli -> factory_agent <-> llm -> governance_runtime`
2. 工作包提交与 Runtime 接收/执行状态
3. 端到端时延、节点成功率与失败原因分布

## 2. 范围

1. 新增运行态 API：
   - `GET /v1/governance/observability/runtime/workpackage-pipeline`
   - `GET /v1/governance/observability/runtime/workpackage-events`
   - `GET /v1/governance/observability/runtime/llm-interactions`
2. 运行态页面新增“治理包链路观测”模块：
   - 阶段漏斗
   - 节点成功率
   - 时延分位（P50/P90）
   - 事件时间线弹窗（含 runtime receipt）
3. 统一筛选维度：`window/workpackage_id/version/client_type/pipeline_stage`
4. LLM 交互观测默认脱敏；admin 导出全量需审计留痕。

## 3. 验收标准

1. 可查看至少 1 条完整链路事件序列：`created -> llm_confirmed -> packaged -> submitted -> accepted -> running -> finished`。
2. `workpackage-pipeline` 返回：`total_workpackages/stage_counts/end_to_end_success_rate/latency_breakdown_ms_p50_p90/runtime_submit_success_rate`。
3. `workpackage-events` 返回：`trace_id/span_id/parent_span_id/source/event_type/occurred_at/status/payload_summary`。
4. `llm-interactions` 返回：`model/base_url/request_count/success_count/failure_count/latency_ms_p50_p90/token_usage/failure_reasons_top/samples`，且 viewer 仅看到脱敏摘要。
5. 页面支持按 `workpackage_id/version/client_type` 联动筛选，点击后可弹窗下钻时间线。
6. No-Fallback：关键依赖不可用时返回显式 `blocked/error`，不允许回退 `in_memory` 或 Dummy runtime。

## 4. 测试要求（TDD）

1. 先补失败用例：
   - `services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py`
   - `services/governance_api/tests/test_runtime_workpackage_events_api_contract.py`
   - `services/governance_api/tests/test_runtime_llm_interactions_api_contract.py`
   - `services/governance_api/tests/test_runtime_workpackage_observability_rbac.py`
   - `tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py`
2. 再实现 Router/Service/Repository 与前端页面模块。
3. 最后执行回归并输出证据：
   - 契约测试报告
   - WebUI 演示截图/日志
   - MVP 验收报告（Markdown + JSON）

## 5. 依赖

1. `runtime.workpackage*` 与 `audit.events` 可查询。
2. Factory CLI、Factory Agent、Runtime 提交链路已写审计事件。
3. No-Fallback 门禁已启用并在测试环境默认生效。

## 6. 非目标

1. 多租户权限体系。
2. 第三方外部可观测平台强依赖（ELK/Tempo）。
3. 历史数据迁移兼容。

## 7. Story 拆解（WBS）

### T1. 事件模型与口径收敛（Architect + Dev）

1. 明确链路阶段枚举：`created/llm_confirmed/packaged/submitted/accepted/running/finished`。
2. 明确事件 source 枚举：`test_client/factory_cli/factory_agent/llm/governance_runtime`。
3. 定义最小字段：`workpackage_id/version/client_type/pipeline_stage/trace_id/span_id/status/occurred_at/runtime_receipt_id`。
4. 输出：字段口径对齐说明 + Repository 查询字段映射。

### T2. API 契约测试先行（Test）

1. 新增并先写失败用例：
   - `test_runtime_workpackage_pipeline_api_contract.py`
   - `test_runtime_workpackage_events_api_contract.py`
   - `test_runtime_llm_interactions_api_contract.py`
2. 新增权限与脱敏测试：
   - `test_runtime_workpackage_observability_rbac.py`
3. 关键断言：
   - No-Fallback 下依赖异常返回 `blocked/error`
   - viewer 返回脱敏摘要，admin 才可全量导出并写审计事件

### T3. 后端聚合与路由实现（Dev）

1. 在 `governance_service` 增加三类聚合方法：
   - `runtime_workpackage_pipeline(...)`
   - `runtime_workpackage_events(...)`
   - `runtime_llm_interactions(...)`
2. 在 `observability.py` 增加三条运行态路由并完成参数校验。
3. 接口错误语义统一：参数错误 `400`，数据缺失空结构，依赖不可用显式 `blocked/error`。

### T4. 页面模块与交互实现（Dev + PM）

1. 运行态页面新增“治理包链路观测”模块：
   - 阶段漏斗
   - 节点成功率
   - 时延分位
2. 支持筛选维度联动：`window/workpackage_id/version/client_type/pipeline_stage`。
3. 点击工作包打开事件时间线弹窗，展示 `receipt` 与关键事件。

### T5. E2E 与验收证据（Test + PM）

1. 新增 WebUI 用例：`tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py`。
2. 覆盖场景：
   - 至少 1 条完整链路可见
   - 弹窗可见 CLI/Agent/LLM/Runtime 事件
   - viewer/admin 脱敏差异正确
3. 产出验收证据：
   - 契约测试结果
   - WebUI 演示截图/日志
   - `MVP` 验收报告（Markdown + JSON）

## 8. 执行顺序与阻塞规则

1. 执行顺序：`T1 -> T2 -> T3 -> T4 -> T5`。
2. 非阻塞问题继续推进；以下情况必须 `blocked` 并上报：
   - 无真实 Runtime 事件导致链路无法验证
   - 无真实 LLM 可用配置导致 LLM 交互观测无法验证
3. 明确禁止：
   - 不允许 `in_memory` fallback
   - 不允许 Dummy runtime 注入主线验收

## 9. 交付清单

1. 路由与服务实现：`services/governance_api/app/routers/observability.py`、`services/governance_api/app/services/governance_service.py`
2. 契约与权限测试：`services/governance_api/tests/test_runtime_workpackage_*`
3. UI E2E 测试：`tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py`
4. 验收报告：`docs/` 下对应 markdown/json 证据
