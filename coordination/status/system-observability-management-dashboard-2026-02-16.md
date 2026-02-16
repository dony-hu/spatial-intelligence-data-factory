# 系统可观测性管理看板交付说明（2026-02-16）

## 目标对齐
面向系统可观测性管理看板交付，满足“看得见、点得进、查得到”：
- 看得见：测试结果总览 + 分层门槛 + 失败分类
- 点得进：证据链接可点击跳转
- 查得到：只读SQL交互查询（白名单/限流/超时/审计）

## 页面入口
- 主页面：`/v1/governance/lab/observability/view`
- 管理数据：`/v1/governance/lab/observability/management/data`
- SQL模板：`/v1/governance/lab/sql/templates`
- SQL历史：`/v1/governance/lab/sql/history`
- SQL查询：`/v1/governance/lab/sql/query`

## 已交付功能
1. 测试结果视图
- 总览字段：`total/executed/passed/failed/skipped/pass_rate/last_run_at/gate_decision`
- 分层门槛：`workpackage/workline/project` 三层
- 失败分类：`failure_type/severity/retryable/gate_impact`
- 证据链接：每条结果附 `evidence_ref`

2. 执行过程视图
- 流程链路：`任务下发 -> 执行 -> 回传 -> 回放 -> 门槛判定`
- 关键字段：`task_batch_id/workpackage_id/status/progress/owner/eta/updated_at`
- 最近事件：时间倒序，补齐至少20条
- 筛选能力：支持按 `owner_line/workpackage_id`

3. SQL交互功能（只读）
- 仅允许 `SELECT/WITH`
- 表白名单限制：`failure_queue/replay_runs`
- LIMIT限制：最大 `_SQL_MAX_ROWS=200`
- 超时限制：`_SQL_TIMEOUT_SEC=2.0`
- 审计日志：写入 SQL history + audit event
- 查询模板/结果表格/分页/错误提示：已接入
- 缺字段兜底：统一显示 `-`

4. 首页摘要与标黄策略
- 首页直接展示“测试结果+执行过程”摘要
- 一键跳转 SQL 交互查询
- 每条摘要展示 `Owner | ETA | 证据链接`
- ETA 或证据缺失自动标黄（`warn-row`）

5. Manifest 可发现性
- `dashboard_manifest.json` 新增 `observability_fields`，披露测试/执行/失败/SQL新增字段

## 主要变更文件
- `services/governance_api/app/routers/lab.py`
- `scripts/dashboard_data_lib.py`
- `services/governance_api/tests/test_lab_api.py`
- `tests/web_e2e/test_observability_live_ui.py`
- `tests/test_dashboard_manifest_observability_fields.py`

## 风险前置披露
- 失败分类目前以 `regressions + 套件映射` 为主，后续可接更细颗粒失败码字典。
- `task_batch_id` 在部分数据源缺失时使用 `workpackage_id` 回填（显示不报错但精度受源数据影响）。
- SQL 查询层安全策略为应用层约束，后续建议在数据网关增加二次隔离。

