# Story: PGO-S6 全量移除代码中 SQLite 相关内容

## 1. Story 目标

在现有代码范围内（`services/`、`packages/`、`scripts/`、`tests/`）移除所有 SQLite 相关实现与入口，确保系统仅保留 PostgreSQL 运行路径。

## 2. 验收标准（Acceptance Criteria）

1. 代码目录中不再存在 SQLite 运行逻辑（如 `sqlite://`、`sqlite3`、`init_governance_sqlite` 等）。
2. 关键脚本默认参数与执行路径仅支持 PostgreSQL。
3. 主线测试不再以 SQLite 作为有效运行前提或等价替代。
4. 仓库卫生脚本可阻断新增 SQLite 代码回流。
5. 清理后 PG-only 回归测试通过，并输出测试报告。

## 3. 影响范围

1. `services/governance_api/*`
2. `services/governance_worker/*`
3. `packages/factory_agent/*`
4. `packages/trust_hub/*`
5. `scripts/*`
6. `tests/*`

## 4. 实施步骤（TDD）

1. 先补失败用例：为 SQLite 入口逐一补“必须 blocked/error”的测试。
2. 删除或替换 SQLite 逻辑：改为 PG-only，并统一错误语义。
3. 更新门禁：在仓库卫生检查中覆盖更多 SQLite 关键字与入口文件。
4. 回归：执行 PG-only 相关测试集与验收脚本，确认无回归。

## 5. 风险与缓解

1. 风险：误删历史工具链中的非主线文件导致演示受损。
- 缓解：清理范围限定在代码运行路径，历史产物与归档文档不动。

2. 风险：测试环境缺少 PG 依赖导致误判。
- 缓解：统一测试入口显式检查 PG 可用性，不可用则清晰失败/跳过。
