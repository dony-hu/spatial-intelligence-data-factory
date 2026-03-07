# Story: MVP-A2 地址治理流程试运行

## 目标

在确认治理方案后，支持对地址治理工作包执行一次 dry run，验证流程可执行且产物完整。

## 验收标准

1. 可通过 CLI 或 Agent 指令触发 dry run。
2. dry run 结果包含状态、输入摘要、输出摘要、失败原因（如有）。
3. 执行后生成最小观测产物（metrics/report）。
4. dry run 失败时不误报成功，错误语义清晰，且必须阻塞等待人工确认，不允许 fallback。

## 开发任务

1. 先补测试：dry run 成功/失败分支用例。
2. 再改实现：补齐试运行入口与结果汇总逻辑。
3. 最后验证：执行样例工作包 dry run 并保存结果。

## 测试用例

1. 有效样例地址输入时 dry run 成功并产出结果。
2. 缺失关键配置时 dry run 失败并返回错误原因，同时记录 `blocked` 等待人工确认。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC B（执行编排）+ EPIC C（证据回传与可观测）。
2. 架构对齐：
- `docs/02_总体架构/系统总览.md` 中 Dryrun 流。
- `docs/02_总体架构/模块边界.md` 中 Agent <-> Runtime 边界。

## 模块边界与 API 边界

1. 所属模块：`factory_agent.dryrun_workflow`、`runtime_orchestrator/worker`、`observability`。
2. 上游入口：CLI/Agent dryrun 指令。
3. 下游依赖：Runtime Entrypoint、Repository、审计/观测事件。
4. API 边界：dryrun 只通过工作包契约执行入口，不允许脚本绕过编排层直接写结果。

## 依赖与禁止耦合

1. 允许依赖：`dryrun_workflow -> runtime adapter -> repository/audit`。
2. 禁止耦合：
- worker 直接写页面缓存替代标准落库。
- dryrun 失败后静默 fallback 为成功响应。
