# 协同控制台（Orchestrator）

本目录用于多 Codex 并行协作的总控与状态收敛。

## 目录约定

- `status/overview.md`：总控汇总状态（只读主视图）
- `status/factory-process.md`：工厂-工艺迭代线状态
- `status/factory-tooling.md`：工厂-工具/执行引擎研发线状态
- `status/factory-workpackage.md`：工厂-工作包编译与下发线状态
- `status/factory-observability-gen.md`：工厂-产线观测代码生成线状态
- `status/line-execution.md`：产线执行线状态

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
