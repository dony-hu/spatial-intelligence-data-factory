# Story: PGO-S2 MVP验收脚本 PG-only 改造

## 目标

将 MVP 验收脚本（unit/integration/full/real-llm-gate）从默认 SQLite 初始化切换到 PG-only。

## 验收标准

1. `run_address_governance_mvp_acceptance*.py` 不再默认 `sqlite:///`。
2. 非 PG `--db-url` 直接失败并给出阻塞语义。
3. profile 验收在 PG 环境下可正常产出 JSON/Markdown。

## 开发任务

1. 先补失败测试：sqlite db_url 应 fail-fast。
2. 再改实现：移除 `init_governance_sqlite` 依赖与 sqlite 分支。
3. 最后回归：`test_mvp_acceptance_script.py` 与 pipeline split。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC C（门禁证据闭环）。
2. 架构对齐：`docs/architecture/system_overview.md`。

## 模块边界与 API 边界

1. 模块：`scripts/run_address_governance_mvp_acceptance*.py`。
2. 边界：验收脚本只消费运行服务与 PG，不维护独立 SQLite 真相源。

## 依赖与禁止耦合

1. 允许：`acceptance script -> governance api/repository -> PG`。
2. 禁止：脚本内置 SQLite 初始化作为主路径。
