# 管理看板研发线任务包：项目介绍与当前状态模块优化

- 下发时间（本地）：2026-02-15 21:28:00 CST
- 负责人：管理看板研发线-Codex
- 目标：把“长文”改造成管理层可快速决策的结构化信息模块

## 先做（内容层）

1. 改成 `管理摘要 + 可展开详情`。
2. 默认只显示 6 行：目标/当前状态/最大风险/阻塞数/48h承诺/决策请求。
3. 顺序固定：当前结论 -> 风险与偏差 -> 本轮承诺 -> 需要管理层决策。
4. 每段最多 3 条 bullet，每条 1.5 行内。
5. 每条都带 `Owner | ETA | 证据链接`。
6. 缺 ETA/证据条目标黄。
7. 左侧结论区不重复右侧状态/进度/ETA。

## 再做（面板层）

1. 左侧拆 4 卡：管理摘要 / 风险雷达Top3 / 48h执行计划 / 管理层关注点。
2. 顶部加 sticky 摘要条：更新时间/总体状态/Go-NoGo/风险数。
3. 增加密度切换：简版（默认）/完整版。
4. 视觉层级：摘要条更深，正文卡片浅底，正文14px，行距1.45。

## 数据源

- `output/dashboard/project_overview.json`
- `output/dashboard/worklines_overview.json`
- `output/dashboard/workpackages_live.json`
- `output/dashboard/dispatch-address-line-closure-002-management-review.json`

## 交付

- 变更说明
- 截图
- 自测记录
