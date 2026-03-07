# UX 设计规格：OBS-RUNTIME-S2-15 人机确认闭环与按工作包执行 E2E 可观测验收（2026-03-02）

## 1. 设计目标与范围

### 1.1 目标
围绕 Story `OBS-RUNTIME-S2-15-人机确认闭环与按工作包执行E2E可观测验收`，设计一套可实现、可测试、可审计的控制台交互，确保：

1. 人机协同链路完整可见（CLI/Agent/LLM/人工确认/Runtime）。
2. 门禁动作严格阻断跳步。
3. 页面可按 `workpackage_id@version` 执行并回查。
4. Web E2E 可通过稳定 `data-testid` 完成自动验收。

### 1.2 范围
本设计仅覆盖运行态可观测控制台，不覆盖研发任务看板、CI/CD 与代码评审流。

## 2. 用户与关键任务

### 2.1 用户角色
1. `viewer`：查看脱敏摘要与运行状态。
2. `oncall`：执行上传、查看完整事件、做一线处置。
3. `admin`：确认发布、查看完整确认轨迹、导出审计证据。

### 2.2 核心任务
1. 发起按工作包执行：上传 CSV + 选择 `workpackage_id@version`。
2. 判断是否可进入下一阶段：基于确认节点与门禁态。
3. 下钻复盘：查看对话收敛、试运行报告、发布确认与 Runtime 事件链路。

## 3. 信息架构（IA）

1. 顶部全局筛选栏
- 时间窗（1h/24h/7d/30d）
- `workpackage_id@version`（支持搜索）
- `client_type`（user/test_client）

2. A 区：执行面板（S2-15 主入口）
- CSV 上传
- 工作包选择
- 执行按钮
- 执行回执（`task_id/runtime_receipt_id`）

3. B 区：确认闭环面板（S2-15 主流程）
- 确认时间线：`confirm_generate -> confirm_dryrun_result -> confirm_publish`
- 当前门禁状态（允许/阻断）
- 操作人、原因、时间、trace

4. C 区：试运行报告面板
- 输入摘要
- `records[]`（逐地址结果）
- `spatial_graph`（批次级唯一图谱）
- 风险与阻断摘要

5. D 区：可观测事件面板
- 事件时间线（中文叙述 / JSON 切换）
- 字段：`source_zh/event_type_zh/status_zh/description_zh/pipeline_stage_zh`
- 关联：`trace_id/workpackage_id/version/actor/occurred_at`

## 4. 主流程与状态机映射

### 4.1 业务唯一主流程
`created -> llm_confirmed -> packaged -> dryrun_finished -> publish_confirmed -> submitted -> accepted -> running -> finished`

### 4.2 UI 状态映射
1. `created/llm_confirmed`
- 确认闭环面板显示“待 confirm_generate”。
- 执行区“提交 Runtime”不可用。

2. `packaged/dryrun_finished`
- 可查看完整 dry-run 报告。
- 未 `confirm_publish` 时，提交动作显示阻断文案。

3. `publish_confirmed/submitted/accepted/running/finished`
- 执行区展示回执与进度。
- 事件面板可完整回放 Runtime 链路。

### 4.3 门禁阻断规则（前后端一致）
1. 无 `confirm_generate`：禁止 `workpackage_packaged`。
2. 无 `confirm_publish`：禁止 `runtime_submit_requested`。
3. 阻断时 UI 必须显示明确原因，不可展示伪成功态。

## 5. 页面级交互设计

### 5.1 上传与执行
1. 上传 CSV 后必须选择工作包版本，未选则执行按钮禁用。
2. 参数校验失败（如仅 `workpackage_id` 无 `version`）显示 `400 INVALID_PAYLOAD` 与修复建议。
3. 执行成功后展示：`task_id/workpackage_id@version/runtime_receipt_id`。

### 5.2 多轮收敛与人工确认
1. 展示 `llm-interactions.request_count`，低于 2 时标记“未满足验收门槛”。
2. 每轮摘要卡必须有 `goal/constraint/decision`。
3. 确认节点点击后可见审计字段：`actor/action/decision/reason/timestamp/trace_id/workpackage_id/version`。

### 5.3 试运行报告下钻
1. 报告结构固定：输入全集 -> `records[]` -> `spatial_graph` -> 统计摘要。
2. `spatial_graph.build_status=PARTIAL` 时高亮 `failed_row_refs`。
3. `address_validation=BLOCKED` 的记录在表格中红色标识，并标注“不贡献图谱”。

### 5.4 事件时间线
1. 默认“中文叙述”模式，支持切换 JSON。
2. 时间线每个节点显示阶段、状态、描述与发生时间。
3. 过滤器联动：切换工作包后自动刷新事件、报告与回执。

## 6. 页面状态与文案规范

### 6.1 空态
1. 无工作包：`当前无可执行工作包，请先完成 confirm_generate 并生成工作包。`
2. 无运行数据：`暂无运行记录，请上传 CSV 并选择 workpackage_id@version 执行。`

### 6.2 阻断态
1. 未确认生成：`流程阻断：缺少 confirm_generate，禁止打包。`
2. 未确认发布：`流程阻断：缺少 confirm_publish，禁止提交 Runtime。`

### 6.3 错误态
1. `400 INVALID_PAYLOAD`：`参数冲突或缺失，请同时提供 workpackage_id 与 version。`
2. Runtime/LLM 异常：统一显示 `blocked/error`，不渲染成功提示。

### 6.4 成功态
`执行已创建：task_id={task_id}，工作包={workpackage_id}@{version}，回执={runtime_receipt_id}`

## 7. E2E 可测性设计（强制）

### 7.1 必备 data-testid
1. `wp-selector`
2. `csv-upload-input`
3. `upload-exec-button`
4. `confirm-timeline-panel`
5. `confirm-generate-status`
6. `confirm-publish-status`
7. `dryrun-report-open`
8. `dryrun-records-table`
9. `dryrun-graph-card`
10. `events-table`
11. `event-view-mode-toggle`
12. `runtime-receipt-id`
13. `gate-blocking-banner`

### 7.2 E2E 验收映射
1. 多轮确认：校验 `request_count >= 2` 且摘要字段完整。
2. 门禁阻断：无确认动作时按钮禁用 + 阻断横幅存在 + 事件无越级状态。
3. 报告完整性：`records[] + spatial_graph + 输入全集 + 统计` 四项齐全。
4. 按工作包执行：上传执行成功，任务/事件/报告同一 `workpackage_id/version` 可回查。
5. 中文可读：中文字段非空，弹窗默认即中文。

## 8. 字段与组件映射

### 8.1 执行组件
- 输入：`workpackage_id/version/ruleset_id`
- 输出：`task_id/runtime_receipt_id/submit_status`

### 8.2 报告组件
- 表格：`records[].normalization/entity_parsing/address_validation/record_decision`
- 图谱卡：`spatial_graph.graph_id/build_status/nodes/edges/metrics/failed_row_refs`

### 8.3 事件组件
- 文本字段：`source_zh/event_type_zh/status_zh/description_zh/pipeline_stage_zh`
- 审计关联：`trace_id/workpackage_id/version/actor/occurred_at`

## 9. 权限与合规体验

1. `viewer`：隐藏确认人明细，仅显示脱敏摘要。
2. `oncall/admin`：显示完整确认轨迹与操作人。
3. 任一确认动作缺少审计字段时，前端显示“审计不完整”告警并禁止显示“闭环完成”。

## 10. 交互流程图（文本）

1. 选择工作包 -> 上传 CSV -> 执行。
2. 系统校验门禁 -> 通过则进入 submitted，阻断则显示原因。
3. 用户查看 dry-run 报告与确认时间线。
4. 通过事件时间线回放 CLI/Agent/LLM/Runtime 全链路。
5. 依据回执与状态确认 `finished`，完成闭环验收。

## 11. 与现有文档对齐说明

1. 与 Story 对齐：状态机、门禁动作、报告结构、中文字段、No-Fallback 全量覆盖。
2. 与 PRD 对齐：保持运行态观测定位，弱化研发流程信息。
3. 与架构对齐：遵循 `UI -> API -> Domain Service` 边界，不在 UI 侧计算核心指标。

## 12. 交付建议

1. 先实现 S2-15 关键页面元素与 `data-testid`，再补齐视觉优化。
2. 先打通“阻断态与审计链路”再做图表细节，保证验收主链路优先。
3. 联调时按 `workpackage_id@version` 作为唯一上下文键，避免跨批次混淆。
