# Story: PGO-S3 契约与工作包 SQLite 引用收敛

## 目标

收敛 contracts/workpackages 中运行时 SQLite 引用，统一改为 PG 引用规范。

## 验收标准

1. `contracts/workpackage.schema.json` 不再把 `sqlite://` 作为运行时合法引用。
2. 主线 workpackage 模板与活跃工作包移除 sqlite 运行引用。
3. 相关校验脚本在遇到 sqlite 运行引用时返回 NO_GO。

## 开发任务

1. 先补失败测试：sqlite ref 校验失败。
2. 再改实现：更新 schema、模板与校验逻辑。
3. 最后回归：workpackage 校验测试与发布门禁测试。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC B、EPIC C。
2. 架构对齐：`docs/architecture/dependency_map.md`。

## 模块边界与 API 边界

1. 模块：`contracts/`、`workpackages/`、`scripts/run_p0_workpackage.py`。
2. 边界：工作包契约只描述 PG 运行依赖。

## 依赖与禁止耦合

1. 允许：`workpackage contract -> pg://<schema>.<table>`。
2. 禁止：`sqlite://...` 进入发布路径。
