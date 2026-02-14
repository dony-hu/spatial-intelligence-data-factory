# Iteration-001 排单与推进

- 日期：2026-02-14
- 总控：Orchestrator
- 目标：建立工厂到产线的首个可执行闭环（含三层可观测）

## 分线排单

1. 工厂-工艺（TC-02）
- 分支：`codex/factory-process`
- 工作树：`/Users/huda/Code/worktrees/factory-process`
- 交付：工艺迭代事件可观测字段落库与查询输出

2. 工厂-工具/执行引擎（TC-03）
- 分支：`codex/factory-tooling`
- 工作树：`/Users/huda/Code/worktrees/factory-tooling`
- 交付：工具/引擎版本与工艺版本关联输出

3. 工厂-工作包（TC-04）
- 分支：`codex/factory-workpackage`
- 工作树：`/Users/huda/Code/worktrees/factory-workpackage`
- 交付：`wp-address-topology-v1.0.1.json`

4. 工厂-观测代码生成（TC-05）
- 分支：`codex/factory-observability-gen`
- 工作树：`/Users/huda/Code/worktrees/factory-observability-gen`
- 交付：工作包内嵌的 L3 观测入口模板

5. 产线执行（TC-06）
- 分支：`codex/line-execution`
- 工作树：`/Users/huda/Code/worktrees/line-execution`
- 交付：单条地址到拓扑任务跑通与结果产物

## 依赖与节奏

- P0：TC-04 与 TC-05 并行，产出工作包实包与观测入口。
- P1：TC-06 在收到实包后执行单条任务。
- P2：TC-02 与 TC-03 全程并行，补齐工厂侧可观测链路。

## 完成定义（本轮）

- 能看到 L1/L2/L3 三层状态。
- 有一个可消费工作包实包。
- 产线单条任务完成并输出结果。
