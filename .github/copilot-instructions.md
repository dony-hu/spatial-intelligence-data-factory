# Copilot 项目指令（BMAD）

## 规则优先级（强制）
1. `AGENTS.md`
2. `bmad/config.yaml`
3. 方法仓模板（BMAD-METHOD）

## 方法仓引用（强制）
1. 默认方法仓路径：`/Users/01411043/code/BMAD-METHOD`。
2. 若默认路径不可达，使用环境变量：`BMAD_METHOD_REPO`。
3. 执行 BMAD 工作流命令（如 `/workflow-status`、`/prd`、`/architecture`、`/create-story`、`/dev-story`）前，优先读取方法仓中的 `_bmad/` 与 `docs/`。
4. 若方法仓不可达，必须在回复中明确“方法仓不可用并采用项目内回退配置”。

## 本项目协作约束
1. 文档默认中文。
2. 代码改动默认测试优先（先失败用例，再实现，再验证）。
3. 研发任务追踪使用 Linear，废弃仓库内手工看板逻辑。
