# 管理看板前端设计交接包（2026-02-15）

## 1. 交付目标
- 面向项目经理日常管理与对外状态同步汇报，重构看板的信息层级与视觉表达。
- 保持现有数据契约不变（不改接口路径、不改字段定义），仅升级前端呈现与交互。
- 输出可直接移交“管理看板研发线”实施。

## 2. 本次设计结论（可直接实现）
- 信息架构改为：`总览KPI -> 分区导航 -> 业务主面板（5块）`。
- 顶部升级为“总控指挥舱”头部：品牌标识、刷新控制、运行健康状态。
- 新增 4 个经营指标卡：
  - 项目健康度
  - 活跃工作线
  - 工作包推进率
  - 质量门禁通过率
- 保留并重排原 5 大业务模块：
  - 项目介绍与当前状态
  - 工作线任务总览
  - 工作包分配与执行进展
  - 系统测试状态
  - 测试进展与详情入口

## 3. 视觉与组件规范
- 设计风格：`Command Deck（管理驾驶舱）`。
- 色彩角色：
  - Brand: `#0f62fe`
  - Accent: `#ff7a1a`
  - Success: `#0b8d53`
  - Danger: `#b93a3a`
- 字体栈：`IBM Plex Sans / Source Han Sans SC / PingFang SC / Microsoft YaHei`。
- 布局规则：
  - 桌面：KPI 4 列、Brief 与 Workline 双列
  - 中屏：KPI 2 列、主区单列
  - 移动：KPI 单列、导航横向滚动
- 关键组件：
  - `hero`：头部状态与操作控制
  - `kpi-card`：指标摘要
  - `section-nav`：锚点跳转
  - `panel`：业务区块容器
  - `task-dialog`：任务提示词复制弹窗

## 4. 交互规则
- 自动刷新：支持 `15s / 30s / 60s`。
- 手动刷新：按钮触发 `refreshAll()`。
- 任务详情：工作线行内“任务详情”按钮弹窗展示并支持复制。
- 健康态联动：头部状态与 KPI 同步由实时数据计算。

## 5. 指标计算口径（前端计算）
- 健康分：
  - 输入：阻塞工作线、门禁失败项、HOLD/NO_GO 包数、工作包平均进度
  - 结果范围：0~100
  - 文案档位：`稳定推进 / 注意风险 / 需要干预`
- 活跃工作线：状态非 `done/closed/completed` 的工作线数。
- 工作包推进率：工作包 `progress` 均值。
- 门禁通过率：
  - `workpackage_schema_ci`
  - `line_feedback_contract`
  - `failure_replay_contract`
  - `overall`

## 6. 数据契约与边界
- 只读取既有文件：
  - `/data/dashboard_manifest.json`
  - `/data/worklines_overview.json`
  - `/data/workpackages_live.json`
  - `/data/test_status_board.json`
  - `/data/pm_brief_zh-CN.json`
  - `/data/pm_brief_zh-CN.md`
  - `/data/workline_dispatch_prompts_latest.json`
- 不新增后端接口、不改 schema、不改字段命名。

## 7. 研发线落地清单
- 以本地原型代码为准同步实现：
  - `/Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/index.html`
  - `/Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/styles.css`
  - `/Users/huda/Code/spatial-intelligence-data-factory/web/dashboard/app.js`
- 实现要求：
  - 保留原有数据读取流程
  - 保持无第三方 CDN 依赖
  - 保障桌面与移动端可用

## 8. 验收标准
- 打开 `http://127.0.0.1:8808/` 可看到：
  - 新版头部 + KPI 条 + 分区导航
  - 5 个业务模块完整加载
  - 工作线“任务详情”弹窗可复制
  - 指标与健康态可随刷新更新
- 任一数据文件缺失时，页面不崩溃，显示降级文案。

## 9. 备注
- 该交接包定位为“前端设计与交互实现基线”，由管理看板研发线按工程规范合并发布。
