# Story: PGO-S1 治理仓储与服务入口 PG-only 硬切

## 目标

将治理仓储层和服务入口从“postgresql 或 sqlite”收敛为“仅 postgresql”，并在非 PG 配置下 fail-fast。

## 验收标准

1. `governance_repository` 不再接受 `sqlite://`。
2. 启动或调用时遇到非 PG 数据源，返回 `blocked/error`。
3. 相关 API/服务测试覆盖 PG-only 判定逻辑。

## 开发任务

1. 先补失败测试：非 PG URL 必须失败。
2. 再改实现：删除 sqlite 分支与方言兼容逻辑。
3. 最后回归：治理 API 仓储相关测试。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC B、EPIC D。
2. 架构对齐：`docs/architecture/module_boundaries.md`、`docs/architecture/dependency_map.md`。

## 模块边界与 API 边界

1. 模块：`services/governance_api/app/repositories`。
2. 边界：服务层通过 Repository 访问 PG，不允许 SQLite 旁路。

## 依赖与禁止耦合

1. 允许：`service -> repository -> postgresql`。
2. 禁止：`service -> sqlite`；在路由中直接方言分支。
