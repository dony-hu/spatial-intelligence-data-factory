# Story：OBS-RUNTIME-S2-15 人机确认闭环与按工作包执行 E2E 可观测验收（完整刷新）

## 1. 故事目标

以“地址治理”场景为基线，交付一个可审计的人机协同闭环：

1. CLI 发起治理意图。
2. Agent 与 LLM 多轮收敛治理逻辑。
3. 人工确认后生成工作包。
4. 试运行并输出完整报告（含输入与治理结果）。
5. 人工确认发布后才允许提交 Runtime。
6. 页面上传 CSV 并按 `workpackage_id@version` 执行。

## 2. 业务流程（唯一主流程）

`created -> llm_confirmed -> packaged -> dryrun_finished -> publish_confirmed -> submitted -> accepted -> running -> finished`

任何跳步都必须阻断并产生日志审计。

## 3. 模拟交互流程（产品示例）

### 3.1 多轮收敛

1. 用户在 CLI 输入治理目标：标准化、实体拆解、地址验证（互联网接口）、空间图谱构建。
2. Agent 向 LLM 询问最小可执行链路与字段定义。
3. LLM 返回方案草案（步骤、输入输出、失败策略）。
4. 用户补充约束（供应商、阈值、节点类型）。
5. Agent 再次请求 LLM 收敛规则并展示给用户。
6. 用户执行 `confirm_generate`，系统才生成工作包。

### 3.2 试运行与发布

1. 用户触发 dry-run。
2. 系统输出完整试运行报告（输入样本 + 治理后结果 + 统计 + 风险）。
3. 用户基于报告决定是否调整。
4. 用户执行 `confirm_publish`，系统才允许提交 Runtime。

### 3.3 页面执行

1. 用户上传地址 CSV。
2. 页面选择 `workpackage_id@version`。
3. 执行后可下钻：对话摘要、确认节点、试运行结论、发布凭证、Runtime 事件链路。

## 4. 输出数据结构（强制）

### 4.1 设计原则

1. 前三项能力按“每条地址”输出：标准化、实体拆解、地址验证。
2. 空间图谱按“每批次”输出：一组输入仅产生一套图谱。

### 4.2 结果模型

顶层结构：

1. `batch_meta`
2. `records[]`（逐地址）
3. `spatial_graph`（批次级唯一）

`records[]` 每项必须包含：

1. `input`（原始地址与来源）
2. `normalization`
3. `entity_parsing`
4. `address_validation`
5. `record_decision`
6. `audit_refs`

`spatial_graph` 必须包含：

1. `graph_id`
2. `graph_version`
3. `build_status`（`SUCCEEDED/PARTIAL/FAILED`）
4. `input_rows_total`
5. `rows_contributed`
6. `rows_skipped`
7. `nodes[]`
8. `edges[]`
9. `failed_row_refs[]`
10. `metrics`（`node_count/edge_count/connected_components`）

### 4.3 约束规则

1. 图谱不得按单行重复输出。
2. 当部分地址失败时允许 `PARTIAL`，但必须列出 `failed_row_refs`。
3. 当 `address_validation` 为 `BLOCKED` 时，该地址不得贡献图谱节点/边。

## 5. 接口契约（含兼容）

### 5.1 upload-batch 扩展

接口：`POST /v1/governance/observability/runtime/upload-batch`

请求可选字段：

1. `workpackage_id`
2. `version`
3. `ruleset_id`

优先级与错误规则：

1. 提供 `workpackage_id+version` 时，按工作包执行。
2. 仅提供 `ruleset_id` 时，走旧逻辑。
3. 同时提供且映射冲突时，返回 `400 INVALID_PAYLOAD`。
4. 仅有 `workpackage_id` 无 `version`，返回 `400 INVALID_PAYLOAD`。

### 5.2 门禁动作

动作枚举：

1. `confirm_generate`
2. `confirm_dryrun_result`
3. `confirm_publish`

阻断规则：

1. 无 `confirm_generate`，不得出现 `workpackage_packaged`。
2. 无 `confirm_publish`，不得出现 `runtime_submit_requested`。

## 6. 可观测字段（中文可读）

`workpackage-events.items[*]` 每条事件必须有：

1. `source_zh`
2. `event_type_zh`
3. `status_zh`
4. `description_zh`
5. `payload_summary.pipeline_stage_zh`

并且必须有审计关联：

1. `trace_id`
2. `workpackage_id`
3. `version`
4. `actor`（若为人工动作）
5. `occurred_at`

## 7. 权限与合规

1. `viewer` 仅看脱敏摘要。
2. `oncall/admin` 可看完整确认轨迹与确认人。
3. 每个确认动作审计字段必填：`actor/action/decision/reason/timestamp/trace_id/workpackage_id/version`。

## 8. 验收标准（可量化）

1. 多轮确认
- `llm-interactions.request_count >= 2`。
- 每轮摘要含 `goal/constraint/decision` 且非空。

2. 门禁阻断
- 缺 `confirm_generate` 时打包请求被阻断且无 `packaged` 事件。
- 缺 `confirm_publish` 时提交请求被阻断且无 `submitted` 事件。

3. 试运行报告完整性
- 报告必须同时包含：
  - 输入数据全集
  - `records[]` 全量治理结果
  - 批次级 `spatial_graph`
  - 统计摘要与阻断原因

4. 按工作包执行
- 上传接口支持 `workpackage_id@version` 并执行成功。
- 执行任务、事件、报告三者可回查同一 `workpackage_id/version`。

5. 中文可读
- 事件中文字段全量非空。
- 页面弹窗可直接阅读，无需二次翻译。

6. No-Fallback
- LLM/Runtime 异常统一 `blocked/error`，禁止伪成功。

## 9. TDD 计划

1. 先补失败用例
- `upload-batch by workpackage`（含冲突与缺参）。
- 门禁阻断（无确认禁止打包/发布）。
- 事件中文字段 E2E。
- 试运行报告结构校验（`records[] + spatial_graph`）。
- Web E2E（上传 CSV -> 选工作包 -> 执行 -> 下钻）。

2. 再实现
- Router/Service/Repository/UI 联动。

3. 最后回归
- `workpackage-pipeline/workpackage-events/llm-interactions`
- `upload-batch by workpackage`
- `RBAC + 脱敏 + 审计`
- `Web E2E`

## 10. WBS（执行任务）

1. T1 门禁状态机（Dev + QA）
2. T2 上传接口与 workpackage 解析（Dev）
3. T3 试运行报告模型（Dev）
4. T4 批次级图谱构建与落盘（Dev）
5. T5 中文事件与对话摘要（Dev）
6. T6 页面交互与下钻（Dev + PM）
7. T7 端到端验收与报告（QA）

## 11. 交付物

1. 代码与测试改动（Router/Service/UI/Tests）。
2. 试运行报告模板与样例产物（JSON + Markdown）。
3. API 契约与 Web E2E 回归报告。
4. Linear 任务与 PR 映射记录。

## 12. 设计输入（Web E2E 前置）

1. 页面设计稿：`docs/ux-runtime-observability-s2-15-page-design-2026-03-02.md`
2. Web E2E 必须基于设计稿中的：
- 信息架构分区
- 错误态与阻断态文案
- `data-testid` 约束
