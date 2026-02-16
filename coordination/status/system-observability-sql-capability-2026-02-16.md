# SQL Capability Report（系统可观测性管理看板）

## 接口
- `GET /v1/governance/lab/sql/templates`
- `GET /v1/governance/lab/sql/history`
- `POST /v1/governance/lab/sql/query`

## 安全与约束
- 只读语句：仅允许 `SELECT/WITH`
- 禁止关键字：`insert|update|delete|drop|alter|create|attach|pragma|vacuum|replace|truncate`
- 白名单表：`failure_queue`, `replay_runs`
- 行数上限：`_SQL_MAX_ROWS = 200`
- 超时：`_SQL_TIMEOUT_SEC = 2.0`
- 审计：
  - 查询历史写入 `output/lab_mode/lab_sql_query_history.json`
  - 审计事件写入 governance repository `tool_call`

## 交互能力
- 模板选择：支持从模板下拉注入 SQL
- 执行结果：表格渲染、分页参数 (`page/page_size`)
- 错误提示：错误码与消息可见
- 空值兜底：`None` -> `-`

## 验证点
- 非只读 SQL（如 `DELETE`）返回 `readonly_enforced`
- 非白名单表返回 `table_whitelist_enforced`
- 超时触发返回 `timeout_enforced`

