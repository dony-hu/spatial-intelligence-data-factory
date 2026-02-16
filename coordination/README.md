# 协同控制台（Orchestrator）

本目录用于多 Codex 并行协作的总控与状态收敛。

## 目录约定

- `status/overview.md`：总控汇总状态（只读主视图）
- `status/project-orchestrator.md`：项目管理总控线状态
- `status/factory-tooling.md`：核心引擎与运行时线状态
- `status/line-execution.md`：产线执行与回传闭环线状态
- `status/trust-data-hub.md`：可信数据Hub线状态
- `status/factory-workpackage.md`：地址算法与治理规则线状态
- `status/test-quality-gate.md`：测试平台与质量门槛线状态
- `status/factory-observability-gen.md`：可观测与运营指标线状态
- `status/engineering-supervisor.md`：工程监理线状态（边界治理与流程合规）

## 汇报格式（统一）

每条线按以下字段更新：

- `进度`：百分比与当前阶段
- `Done`：本轮完成项
- `Next`：下一步动作
- `Blocker`：阻塞项（没有则写`无`）
- `ETA`：预计完成时间
- `Artifacts`：代码路径/产物路径/提交号

## 规则

- 总控只写 `overview.md`，不替代子线写细节。
- 子线不得越权改动其他子线状态文件。
- 状态更新建议每 30-90 分钟一次。
- 工作线命名以本文件为准，禁止在派单与看板中使用旧命名别名。
- 研发角色体系统一采用 Build-time 口径（治理角色 + 工作线角色 + Agent 能力域），映射规范见 `docs/codex-bmad-role-mapping-v1-2026-02-15.md`。
- 运营使用者角色（Run-time）不得写入研发派单责任字段。
- 每次任务推进必须同步刷新看板落盘：`task_dispatched`、`progress_refreshed`、`status_collected`、`test_synced` 四类事件均需写入 `output/dashboard/dashboard_events.jsonl`，并刷新 `project_overview/worklines_overview/workpackages_live/test_status_board/dashboard_manifest`。
- 派单时间口径统一使用本地时间（CST），下发提示词与看板展示不再使用 UTC 字段。
- 工程边界红线：
  - 测试线不得修改研发代码。
  - 开发线不得修改测试用例以规避失败。
  - 看板研发线只负责看板研发，不得改生产系统研发和测试逻辑。
  - 禁止通过 mock/桩数据绕过真实链路验收（经审批的隔离测试除外且需明示）。
  - 工程监理线仅输出项目级监理审计报告，不修改任何项目工作输出。

## 派单字段最小集（研发强制）

`coordination/dispatch/*.md` 任务条目必须包含以下字段：

- `workline`：8 条协同工作线之一
- `A_role`：治理最终负责角色
- `R_owner`：工作线执行 Owner
- `agent_capabilities`：主 Agent 能力域（建议 1-2 个）
- `skill_profile`：BMAD skills 配置档（对应角色映射文档中的默认 skill 链）
- `skill_entry`：本次执行起始 skill（如 `specify` / `plan` / `implement`）
- `skill_exit_gate`：本次完成门禁（如 `analyze_pass` / `checklist_pass`）
- `go_no_go_gate`：可量化验收门槛
- `evidence_paths`：证据路径

缺失字段时，任务状态不得从“已派单”推进到“验收中/已完成”。

## BMAD Skills 执行约定（研发期）

- 默认 skill 链映射见：`docs/codex-bmad-role-mapping-v1-2026-02-15.md`
- 同一任务默认只允许 1 条主 skill 链，避免并发执行导致口径冲突
- `analyze/checklist` 未通过时，状态必须保持 `NO_GO`，不得直接标记“已完成”
