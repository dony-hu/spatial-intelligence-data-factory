# Story: MVP-A5 可信数据 Hub 能力沉淀

## 目标

在工厂 CLI/Agent 交互过程中同步构建可信数据 Hub，沉淀外部工具/API 能力与可信互联网数据样例。

## 验收标准

1. 至少支持 2 类外部能力注册（如地图 API、检索 API）。
2. 可存储并查询数据源元数据（provider、endpoint、状态）。
3. 可沉淀并查询最小可信数据样例集。
4. 数据写入与读取过程有基础校验与错误语义，外部能力异常时必须阻塞并等待人工确认。

## 开发任务

1. 先补测试：数据源注册、查询、重复写入、非法输入用例。
2. 再改实现：扩展 Trust Hub 数据模型（能力+样例数据）。
3. 最后验证：通过 CLI/Agent 完成一次能力沉淀与查询回读。

## 测试用例

1. 注册高德/百度数据源后可查询到 provider 与 endpoint。
2. 写入可信样例数据后可按 source 检索。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC A（结果可信）+ EPIC B（可观测执行）+ EPIC D（能力沉淀）。
2. 架构对齐：
- `docs/02_总体架构/系统总览.md` Trust 增强流。
- `docs/02_总体架构/依赖关系.md` trust_meta/trust_data 依赖关系。

## 模块边界与 API 边界

1. 所属模块：`trust_hub`、`trust_meta/trust_data repository`、`governance query adapter`。
2. 上游入口：CLI/Agent 能力注册与数据沉淀请求。
3. 下游依赖：外部工具/API 适配器、可信数据持久化层。
4. API 边界：Trust Hub 对上暴露能力接口，不暴露底层外部 provider 差异细节。

## 依赖与禁止耦合

1. 允许依赖：`trust_hub -> provider adapter -> repository`。
2. 禁止耦合：
- `address_core` 与 `trust_hub` 双向直接调用形成循环依赖。
- 以本地文件替代数据库为主真相源且无显式模式标识。
