# Epic3 WorkPackage 旧版清理评审与推进任务（2026-03-03）

## 1. 本次清理结论（已完成）

1. 已删除旧版根契约：`contracts/workpackage.schema.json`。
2. 已删除旧版根目录工作包：`workpackages/wp-*.json`（共 20 个）。
3. `run_p0` 相关脚本已改为从 `workpackage_schema/registry.json` 解析当前 schema，不再硬编码旧路径。
4. 已新增固化检查命令与 CI workflow，防止旧版内容回流。

## 2. 已固化的命令 / workflow

1. 新增命令脚本：`scripts/check_workpackage_cleanup.sh`
2. Makefile 目标：`make check-workpackage-cleanup`
3. CI 工作流：`.github/workflows/p0-workpackage.yml`
   - 触发路径已切换到 `workpackage_schema/**` 等新版资产
   - 门禁已改为执行 `./scripts/check_workpackage_cleanup.sh`

## 3. 回归结果

执行：`./scripts/check_workpackage_cleanup.sh`

- `tests/test_workpackage_v1_cleanup_guard.py`：通过
- `tests/test_workpackage_blueprint_schema_versioning.py`：通过
- `tests/test_workpackage_schema_address_case_example.py`：通过
- `tests/test_workpackage_schema_companion_artifacts.py`：通过
- `tests/test_run_p0_workpackage.py`：通过
- 合计：`15 passed`

## 4. 需要 BM Master 统一推进的具体任务

1. 任务：清理历史状态文档中的 legacy 路径残留（`coordination/`、`docs/` 非 archive）。
   - 目标：禁止出现已删除的 `workpackages/wp-*.json` 作为“当前有效路径”。
   - 验收：`rg "workpackages/wp-" coordination docs README.md` 仅允许出现 `[legacy 已清理]` 标注或 archive 历史说明。

2. 任务：统一 P0 报告命名与当前 schema 版本语义。
   - 目标：将 `output/workpackages/wp-core-engine-p0-stabilization-v0.1.0.report.json` 命名从 legacy `wp-*` 迁移到 schema-v1 语义命名。
   - 验收：脚本默认输出文件名与 README 说明一致，且不再暗示旧版根目录工作包仍存在。

3. 任务：补一个仓库卫生检查（可并入 `scripts/check_repo_hygiene.sh`）。
   - 目标：阻断新增 `contracts/workpackage.schema.json` 与 `workpackages/wp-*.json`。
   - 验收：新增文件一旦出现，CI 直接失败并输出明确错误信息。

4. 任务：将 `run_p0_workpackage.py` 的输入契约与 `workpackage_schema v1` 做正式对齐评审。
   - 目标：确认 `line_feedback_contract` 等字段是迁移到 v1 扩展、还是将 P0 gate 逻辑拆离为独立契约。
   - 验收：形成一份架构决策记录（ADR）并更新对应测试基线。

## 5. 风险与说明

1. `output/` 与 `archive/` 中存在历史产物对旧路径的引用，属于历史证据，不建议直接删除；建议通过“历史目录白名单”治理。
2. 当前仓库存在大量并行改动（非本次清理引入），本次仅对 workpackage 旧版清理范围内文件做了最小必要变更。
