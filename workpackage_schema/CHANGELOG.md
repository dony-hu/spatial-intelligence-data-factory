# Workpackage Schema 协议变更日志

## v1（2026-03-03）
- 首次发布 `workpackage_schema.v1.schema.json`。
- 固定顶层必填字段：
  - `schema_version`
  - `mode`
  - `workpackage`
  - `architecture_context`
  - `io_contract`
  - `api_plan`
  - `execution_plan`
  - `scripts`
- 明确人工门禁字段：
  - `execution_plan.gates.confirm_generate`
  - `execution_plan.gates.confirm_dryrun_result`
  - `execution_plan.gates.confirm_publish`
- 明确 LLM 校验失败处理策略字段：
  - `execution_plan.failure_handling.on_schema_mismatch = continue_llm_interaction_until_valid`

## v1 patch（2026-03-05）
- 新增 nanobot 编排记忆对象协议：`schemas/v1/orchestration_context.v1.schema.json`。
- 新增编排记忆样例：`examples/v1/nanobot_orchestration_memory.v1.json`。
- `registry.json` 为 `v1.companion_artifacts` 增加：
  - `orchestration_context_schema`
  - `orchestration_context_example`

## v1 patch（2026-03-06，I/O binding）
- 直接升级 `schemas/v1/workpackage_schema.v1.schema.json`，新增工程化 I/O 绑定能力：
  - `io_contract.input_bindings[]`
  - `io_contract.output_bindings[]`
  - `scripts[].consumes`
  - `scripts[].produces`
  - `execution_plan.steps[].input_bindings`
  - `execution_plan.steps[].output_bindings`
- 更新 `examples/v1/address_batch_governance.workpackage_schema.v1.json` 以匹配新字段。
- 新增设计说明文档：
  - `docs/04_系统组件设计/工作包协议IO绑定工程化设计.md`
- 目标：让 `v1` 直接同时表达“数据格式”和“协议绑定”，支撑工厂生成可直接运行的读写脚本骨架。

## v1 patch（2026-03-06，人机协同状态机）
- 升级 `schemas/v1/orchestration_context.v1.schema.json`：
  - 新增 `interaction_state`
  - 结构化 `blocker_ticket`
  - 结构化 `gate_state`
- 更新 `examples/v1/nanobot_orchestration_memory.v1.json`：
  - 用真实用户介入场景展示 `WAIT_USER_INPUT`
  - 明确恢复点、原因码、用户动作与 timeline
- 新增设计文档：
  - `docs/04_系统组件设计/工厂Agent人机协同状态机.md`

## 版本管理规则（强制）
- 主版本（Major）：删除必填字段、改变字段语义、改变枚举含义。
- 次版本（Minor）：新增可选字段或可选枚举，不破坏旧消费者。
- 修订版本（Patch）：修正文档、注释、示例，不改变结构约束。
- 新版本发布前必须：
  1. 新增对应 schema 文件。
  2. 更新 `registry.json` 的 `current_version` 与 `versions`。
  3. 更新本文件变更记录。
  4. 增加/更新自动化测试验证版本索引与关键必填字段。
