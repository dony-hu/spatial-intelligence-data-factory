# Story: MVP-A3 工作包发布到数据治理 Runtime

## 目标

将生成的地址治理工作包发布到数据治理 Runtime，并可由 Runtime 识别与执行。

## 验收标准

1. 工作包包含完整目录：代码、skills、入口脚本、元数据、观测文件。
2. 发布动作可被 Runtime 识别并记录版本信息。
3. 发布后可触发一次执行并返回运行结果。
4. 发布失败必须 fail-fast 并返回明确错误，阻塞后续流程，待人工确认后再重试。

## 开发任务

1. 先补测试：发布契约校验与缺文件失败用例。
2. 再改实现：完善工作包发布逻辑与版本标识。
3. 最后验证：完成一次发布+执行闭环。

## 测试用例

1. 合法工作包发布成功，Runtime 可读取元数据。
2. 缺失 `workpackage.json` 时发布失败并返回错误码。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC B（发布与运行编排）+ EPIC C（证据与门禁）。
2. 架构对齐：
- `docs/architecture/system_overview.md` 发布执行流。
- `docs/architecture/dependency_map.md` 中 Agent/Runtime/Repository 依赖图。

## 模块边界与 API 边界

1. 所属模块：`publish_workflow`、`runtime`、`repository`、`audit`。
2. 上游入口：CLI/API publish 指令。
3. 下游依赖：Runtime 发布接口、版本持久化、执行触发、证据归档。
4. API 边界：发布 API 仅接受工作包契约输入，不暴露内部存储细节。

## 依赖与禁止耦合

1. 允许依赖：`agent publish workflow -> runtime adapter -> repository`。
2. 禁止耦合：
- 直接在 CLI 中拼装 SQL 写入发布记录。
- 绕过版本契约直接触发运行时执行。
