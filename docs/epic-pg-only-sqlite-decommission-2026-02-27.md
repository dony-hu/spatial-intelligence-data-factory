# Epic - PG-ONLY 与 SQLite 运行时清理专项（2026-02-27）

## 1. Epic 目标

将地址治理主链路从“PG + SQLite 混用”收敛为“PG-only 权威数据源”，并在代码、测试、验收、契约、门禁五个层面形成硬约束，防止 SQLite 回流到运行主链路。

## 2. 背景与触发

当前架构已明确多 schema PG 基线，但仓库中仍存在运行时 SQLite 路径（验收脚本默认 SQLite、仓储层允许 sqlite://、部分契约允许 sqlite://）。

这与以下文档目标存在偏差：

1. `docs/prd-spatial-intelligence-data-factory-2026-02-27.md`
2. `docs/architecture-unified-pg-multi-schema-v1-2026-02-27.md`
3. `docs/architecture/system_overview.md`
4. `docs/architecture/module_boundaries.md`
5. `docs/architecture/dependency_map.md`

## 3. In Scope

1. 治理 API/仓储层：禁止 sqlite:// 作为持久化运行模式。
2. MVP 验收脚本：默认与仅支持 PG（real-llm-gate 同步遵循）。
3. workpackage/contracts：运行时引用仅允许 PG 格式。
4. 主线测试：切换为 PG-only，并移除/重写依赖 SQLite 的主线测试假设。
5. CI 门禁：新增 SQLite 回流检测，出现运行主链路 SQLite 依赖即 NO_GO。
6. 代码全量清理：移除现有代码中的 SQLite 相关实现、脚本入口、测试依赖与运行配置。

## 4. Out of Scope（本 Epic 不做）

1. `archive/` 历史文档与历史证据产物回写。
2. 非代码资产中的历史文本记录（如旧报告提及 SQLite）批量改写。
3. 非主线实验目录（`output/` 历史产物）的大规模清理。

## 5. Story 拆解

1. PGO-S1：治理仓储与服务入口 PG-only 硬切
2. PGO-S2：MVP 验收脚本与 profile 全量 PG-only 改造
3. PGO-S3：workpackage/contracts 的 SQLite 引用收敛
4. PGO-S4：主线测试集 PG-only 重构与阻塞项清理
5. PGO-S5：CI/仓库卫生增加 SQLite 回流硬门
6. PGO-S6：全量移除代码中 SQLite 相关内容

## 6. DoD（Epic 完成定义）

1. 主线运行路径（CLI/Agent/API/Worker/Acceptance）不再接受 sqlite://。
2. `DATABASE_URL` 非 PG 时，关键流程 fail-fast 且返回 `blocked/error`。
3. workpackage 与 contracts 不再出现运行时 sqlite:// 合法模式。
4. PG-only 主线测试通过，并产出最新证据报告。
5. CI 新增“SQLite 回流检测”并启用阻断。
6. 现有代码目录（`services/`、`packages/`、`scripts/`、`tests/`）中不再保留 SQLite 运行逻辑与依赖入口。

## 7. 风险与缓解

1. 风险：历史测试与脚本大量依赖 SQLite，迁移初期失败面扩大。
- 缓解：按 Story 分批替换，先主链路后扩展链路，分层放闸。

2. 风险：PG 环境依赖导致本地执行门槛提升。
- 缓解：提供统一 docker-compose / env 模板与最小启动脚本。

3. 风险：误伤历史归档资产。
- 缓解：明确仅治理“运行主链路”，历史目录标注 out-of-scope。

## 8. 验收证据

1. 测试日志：`output/test-reports/*`
2. 验收产物：`output/acceptance/*`
3. PRD/架构确认报告：新增 PG-only 专项确认文档（开发完成后输出）
