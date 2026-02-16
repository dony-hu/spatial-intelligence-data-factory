# 管理看板研发线任务包：工程监理线可视化

- 下发时间（本地）：2026-02-15 21:12:00 CST
- 负责人：管理看板研发线-Codex
- 目标：在管理面板展示工程监理线及其任务详情

## 要做什么

1. 工作线总览新增 `工程监理线` 行。
2. 任务详情弹窗可展示工程监理线的任务包与提示词。
3. 仅展示本地下发时间（不展示 UTC）。
4. 缺字段显示 `-`，不报错，不阻塞刷新。

## 数据源

- `output/dashboard/worklines_overview.json`
- `output/dashboard/workline_dispatch_prompts_latest.json`
- `output/dashboard/dashboard_manifest.json`

## 边界

- 仅改看板前端与看板数据读取逻辑。
- 不改生产系统研发代码。
- 不改测试逻辑与测试数据。

## 交付物

- 变更说明
- 截图
- 自测记录
