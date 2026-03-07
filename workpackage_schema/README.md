# Workpackage Schema（版本化管理）

本目录用于统一管理 Factory Agent-LLM-治理 Runtime 之间的工作包协议与配套工件。

## 目录说明
- `registry.json`
  - 全版本索引与当前生效版本（唯一入口）。
- `CHANGELOG.md`
  - 协议变更记录。
- `schemas/<version>/`
  - 存放该版本 schema 文件，例如 `schemas/v1/workpackage_schema.v1.schema.json`。
  - 编排记忆对象协议也在此目录维护，例如 `schemas/v1/orchestration_context.v1.schema.json`。
- `templates/<version>/`
  - 存放该版本配套模板（README 模板、目录结构模板等）。
- `examples/<version>/`
  - 存放该版本案例实例。

## 版本规则
- `major`：删除必填字段或改变字段语义（破坏兼容）。
- `minor`：新增可选字段（向后兼容）。
- `patch`：修正文档、注释与模板，不改变结构约束。

## 配套模板（强制）
每个 schema 版本必须提供并登记：
1. `README 模板`
2. `目录结构模板`
3. `编排上下文/记忆对象协议（如适用）`

登记位置：
- `registry.json -> versions.<version>.companion_artifacts`

## 管理约束（强制）
1. 新增 schema 版本时，必须创建对应目录：
   - `schemas/<version>/`
   - `templates/<version>/`
   - `examples/<version>/`
2. `registry.json` 必须登记：
   - `schema_file`
   - `companion_artifacts`
   - `examples`
3. 任何消费者读取版本时只能通过 `registry.json` 解析，不允许硬编码文件路径。

## 推荐阅读顺序

1. `docs/04_系统组件设计/工厂Agent与工作包工程化设计.md`
   - 先看总设计，理解 Factory Agent、工作包协议、记忆对象、人机协同的整体关系。
2. `docs/04_系统组件设计/工作包协议IO绑定工程化设计.md`
   - 再看工作包 I/O binding 设计。
3. `docs/04_系统组件设计/工厂Agent人机协同状态机.md`
   - 最后看用户介入、阻塞与恢复状态机。
