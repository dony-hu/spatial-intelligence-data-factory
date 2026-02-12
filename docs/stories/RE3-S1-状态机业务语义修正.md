# Story: RE3-S1 状态机业务语义修正

## 目标

让 `COMPLETED` 仅表示业务产物有效通过门禁。

## 验收标准

1. Gate 失败时不可进入 `COMPLETED`。
2. 成功路径中 `COMPLETED` 前必须有 Gate PASS 记录。
3. `quick_test` 不出现“completed + 空图谱”记录。

## 开发任务

1. 修订 `tools/factory_workflow.py` 完成态触发条件。
2. 修订执行结果对象，明确 gate 结果。
3. 增加状态机集成测试。
