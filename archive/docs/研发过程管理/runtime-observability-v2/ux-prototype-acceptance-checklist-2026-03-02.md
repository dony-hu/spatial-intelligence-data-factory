# 最小验收检查清单：OBS-RUNTIME-S2-15 可交互原型

## 1. 门禁阻断
1. 默认未确认发布时，点击“上传并执行”显示阻断横幅。
2. 执行前若缺少 `workpackage_id@version`，按钮禁用或提示错误。

## 2. 人机确认闭环
1. 页面可见确认时间线：`confirm_generate -> confirm_dryrun_result -> confirm_publish`。
2. 每个确认节点可查看审计字段（actor/action/decision/reason/timestamp/trace_id）。

## 3. 试运行报告
1. 报告含输入摘要、`records[]`、`spatial_graph`。
2. `PARTIAL` 状态显示 `failed_row_refs`。

## 4. 事件下钻
1. 事件列表可切换“中文叙述/JSON”。
2. 中文字段 `source_zh/event_type_zh/status_zh/description_zh/pipeline_stage_zh` 非空。

## 5. E2E 可测性
1. 以下 testid 全部存在且可见：
- `wp-selector`
- `csv-upload-input`
- `upload-exec-button`
- `confirm-timeline-panel`
- `dryrun-report-open`
- `dryrun-records-table`
- `dryrun-graph-card`
- `events-table`
- `event-view-mode-toggle`
- `runtime-receipt-id`
- `gate-blocking-banner`
