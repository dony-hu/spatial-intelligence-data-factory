# 管理看板研发线下一轮合并任务包

- 下发时间（本地）：2026-02-15 21:35:00 CST
- 负责人：管理看板研发线-Codex
- 目标：合并交付“工程监理线可视化”与“项目介绍模块优化”

## 合并内容

1. 工程监理线可视化：总览可见 + 详情可见 + 边界说明可见
2. 项目介绍模块优化：管理摘要+展开详情、6行默认、结论先行四段
3. 面板交互：4卡片区 + sticky摘要条 + 密度切换（默认简版）
4. 视觉规范：摘要深底、正文浅底、14px、行距1.45

## 关键规则

- 每条摘要信息必须带 `Owner | ETA | 证据链接`
- 缺 ETA/证据条目标黄
- 左侧结论区不得重复右侧状态/进度/ETA
- 缺字段统一显示 `-`，不得报错

## 数据源

- `output/dashboard/worklines_overview.json`
- `output/dashboard/workline_dispatch_prompts_latest.json`
- `output/dashboard/project_overview.json`
- `output/dashboard/workpackages_live.json`
- `output/dashboard/dispatch-address-line-closure-002-management-review.json`
- `output/dashboard/dashboard_manifest.json`

## 交付物

- 变更说明
- 截图
- 自测记录
