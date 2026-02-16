# Iteration-005 派单：管理看板下一轮合并任务包

- 下发时间（本地）：2026-02-15 21:35:00 CST
- 工作线：管理看板研发线
- 负责人：管理看板研发线-Codex
- 目标：将“工程监理线可视化”与“项目介绍与当前状态模块优化”合并为一轮交付

## 研发治理字段（强制）

- workline: 管理看板研发线
- A_role: 平台PM
- R_owner: 管理看板研发线负责人（Codex）
- agent_capabilities: 编排 + 审计
- skill_profile: project_orchestrator_v1
- skill_entry: speckit.tasks
- skill_exit_gate: checklist_pass
- go_no_go_gate:
	- 验收清单全部通过
	- 夜间回归 `suite_web_e2e_catalog` 恢复 `passed`
	- 证据链（变更说明/截图/自测记录）齐全
- evidence_paths:
	- web/dashboard/index.html
	- web/dashboard/app.js
	- web/dashboard/styles.css
	- output/dashboard/dashboard_manifest.json
	- output/dashboard/worklines_overview.json
	- output/dashboard/test_status_board.json

## 合并范围

1. 工程监理线可视化与任务详情展示
2. 项目介绍与当前状态模块双层结构改造
3. 左侧4卡片 + 顶部sticky摘要 + 密度切换

## 统一交付口径

### A. 工程监理线可视化（来自上一轮任务）

- 工作线总览可见：工程监理线（负责人/状态/进度/ETA）
- 任务详情弹窗可见：监理任务包与提示词
- 明示边界：工程监理线仅输出审计报告，不修改项目工作输出

### B. 项目介绍与当前状态优化（新增并合并）

- 默认仅展示6行管理摘要（目标/当前状态/最大风险/阻塞数/48h承诺/决策请求）
- 详细内容折叠到“展开全部”
- 结构顺序固定：当前结论 -> 风险与偏差 -> 本轮承诺 -> 需要管理层决策
- 每条信息必须带：Owner | ETA | 证据链接
- 缺 ETA/证据条目标黄

### C. 面板结构与交互

- 左侧拆4卡：管理摘要 / 风险雷达Top3 / 48h执行计划 / 管理层关注点
- 顶部 sticky 摘要条：更新时间 / 总体状态 / Go-NoGo / 风险数
- 密度切换：简版（默认）/ 完整版

### D. 视觉规范

- 摘要条背景更深一档
- 正文卡片浅底
- 正文字体 14px
- 列表行距 1.45

## 数据源

- `output/dashboard/worklines_overview.json`
- `output/dashboard/workline_dispatch_prompts_latest.json`
- `output/dashboard/project_overview.json`
- `output/dashboard/workpackages_live.json`
- `output/dashboard/dispatch-address-line-closure-002-management-review.json`
- `output/dashboard/dashboard_manifest.json`

## 验收标准

- [ ] 工程监理线在总览与详情均可见
- [ ] 项目介绍模块双层结构生效
- [ ] 6行摘要默认展示，详情可展开
- [ ] 四段顺序正确，且每段不超过3条bullet
- [ ] 每条显示 Owner|ETA|证据链接
- [ ] 缺ETA/证据标黄
- [ ] 左侧不重复右侧状态信息
- [ ] 四卡片 + sticky + 密度切换生效
- [ ] 提交变更说明 + 截图 + 自测记录
