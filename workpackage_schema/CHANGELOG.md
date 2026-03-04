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

## 版本管理规则（强制）
- 主版本（Major）：删除必填字段、改变字段语义、改变枚举含义。
- 次版本（Minor）：新增可选字段或可选枚举，不破坏旧消费者。
- 修订版本（Patch）：修正文档、注释、示例，不改变结构约束。
- 新版本发布前必须：
  1. 新增对应 schema 文件。
  2. 更新 `registry.json` 的 `current_version` 与 `versions`。
  3. 更新本文件变更记录。
  4. 增加/更新自动化测试验证版本索引与关键必填字段。
