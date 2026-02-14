# Iteration-001 R2 总控派单

- 日期：2026-02-14
- 角色：Orchestrator
- 策略：承认并行改动有效，按边界治理继续推进

## R2 任务

1. Factory-Process（TC-02）
- 补齐迭代事件写入字段（版本/原因/时间）
- 提供一条可查询样例

2. Factory-Tooling（TC-03）
- 输出工具包与引擎版本映射字段
- 提供兼容矩阵最小样例

3. Factory-WorkPackage（TC-04）
- 发布 `wp-address-topology-v1.0.2.json`
- 补齐下发元信息与回滚信息

4. Factory-Observability-Gen（TC-05）
- 在 `process_compiler/tool_generator` 接入自动观测生成
- 输出步骤级错误码字段

5. Line-Execution（TC-06）
- 补单条显式任务入口
- 产出失败回放样例并回传

## 收敛门槛

- 工作包、观测包、产线结果三者版本一致
- 每条线状态卡包含 Done/Next/Blocker/ETA
- 不再出现跨线误改状态文件

## R2 修正指令（立即生效）

- 非 `Factory-Process` 线路禁止改动 `coordination/status/factory-process.md`
- 各线路只允许更新各自状态文件：
  - Factory-Process -> `factory-process.md`
  - Factory-Tooling -> `factory-tooling.md`
  - Factory-WorkPackage -> `factory-workpackage.md`
  - Factory-Observability-Gen -> `factory-observability-gen.md`
  - Line-Execution -> `line-execution.md`
