# Dashboard Data Contract

本说明定义项目看板数据文件契约、触发更新规则与使用方式。所有文件均由脚本自动生成，前端可直接 `fetch`。

## 目录
固定输出目录：
- `./output/dashboard/`

## 文件清单
- `project_overview.json`
- `worklines_overview.json`
- `workpackages_live.json`
- `test_status_board.json`
- `dashboard_manifest.json`
- `dashboard_events.jsonl`

## 生成脚本
全量构建：
```bash
python3 ./scripts/build_dashboard_data.py
```

事件增量更新：
```bash
python3 ./scripts/update_dashboard_on_event.py \
  --event-type task_dispatched \
  --workpackage-id wp-core-engine-p0-stabilization-v0.1.0 \
  --summary "下发P0稳定化工作包" \
  --operator "orchestrator"
```

## 事件类型与刷新规则
支持事件：
- `task_dispatched`
- `progress_refreshed`
- `status_collected`
- `test_synced`
- `release_decision_changed`

刷新规则：
- `task_dispatched` / `progress_refreshed` / `status_collected` / `release_decision_changed`
  - 刷新并落盘：`project_overview.json`、`worklines_overview.json`、`workpackages_live.json`
- `test_synced` / `release_decision_changed`
  - 刷新并落盘：`test_status_board.json`
- 所有事件都会刷新：`dashboard_manifest.json`
- 所有事件都会追加一条：`dashboard_events.jsonl`

## Manifest 用法
前端只需读取：`dashboard_manifest.json`
- `files` 字段给出四个看板数据文件名
- `refresh_policy` 给出事件驱动和计划刷新策略（`*/15 * * * *`）

## 编码约束
- 全部 JSON 文件均为 UTF-8
- 缩进为 2 空格
- 字段稳定，不因空值缺失（未取到数据时使用空字符串、空数组、`false` 或 `HOLD`）
