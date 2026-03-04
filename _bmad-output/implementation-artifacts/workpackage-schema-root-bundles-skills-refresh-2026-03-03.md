# WorkPackage Schema / Bundles / Skills 全面清理与刷新（2026-03-03）

## 结论

已按最新架构要求完成三项改造：

1. `workpackage_schema` 已上移为项目一级目录（`/workpackage_schema`）。
2. 过时 WorkPackage Bundle 已从 `/workpackages/bundles` 清理。
3. `skills` 已纳入 workpackage 正式协议，并同步刷新 schema/template/sample。

## 1) 目录与架构对齐

### 已完成

1. 目录迁移：
   - 从 `contracts/workpackage_schema` 迁移到 `workpackage_schema`。
2. 引用收敛：
   - 脚本、测试、README、workflow、状态文档中相关路径已改为 `workpackage_schema/...`。
3. 架构文档补充：
   - 在 `docs/architecture-spatial-intelligence-data-factory-2026-02-28.md` 新增 **“7.1 WorkPackage Schema 与 Contracts 关系”**，明确：
     - `workpackage_schema` 位于项目一级目录；
     - 通过 `workpackage_schema/registry.json` 进行版本路由；
     - `contracts/` 作为其他契约域继续存在并与治理规范对齐。

## 2) 过时 bundles 清理

### 清理规则

- 以“缺少 `workpackage.json` 的 bundle 目录”为过时目录。

### 已删除目录

1. `workpackages/bundles/address-topology-v1.0.1`
2. `workpackages/bundles/address-topology-v1.0.2`
3. `workpackages/bundles/addrob_v1-1-0-0`
4. `workpackages/bundles/proc_v1-1-0-2`
5. `workpackages/bundles/prochu_v1-1-0-0`

### 清理后现状

- 当前 `workpackages/bundles/*` 均包含 `workpackage.json`，满足最小结构约束。

## 3) Skills 协议化（schema/template/sample）

### Schema 变更

文件：`workpackage_schema/schemas/v1/workpackage_schema.v1.schema.json`

1. 顶层 `required` 新增：`skills`。
2. 新增 `skills` 字段定义：
   - 类型：`array`，`minItems: 1`
   - 每项必须包含：`skill_id/name/path/purpose`
   - `path` 强制匹配：`skills/*.md`
3. `$id` 已改为一级目录语义：
   - `https://spatial-intelligence-data-factory/workpackage_schema/workpackage_schema.v1.schema.json`

### Template 变更

1. `workpackage_schema/templates/v1/workpackage_bundle.structure.v1.md`
   - 新增 `skills/` 目录结构。
   - 明确 `workpackage.json.skills[].path` 必须可解析到 `skills/`。
2. `workpackage_schema/templates/v1/workpackage_bundle.README.v1.md`
   - 新增 `skills/` 职责说明。

### Sample 变更

文件：`workpackage_schema/examples/v1/address_batch_governance.workpackage_schema.v1.json`

1. 新增 `skills` 示例数组（2 条），覆盖：
   - 必选技能（`required: true`）
   - 可选技能（`required: false`）

## 4) 测试与门禁

### 新增/更新守卫

1. `tests/test_workpackage_v1_cleanup_guard.py`
   - 断言 `workpackage_schema` 在项目一级目录；
   - 断言 `contracts/workpackage_schema` 不再存在；
   - 断言 bundles 不存在缺少 `workpackage.json` 的过时目录；
   - 断言架构文档明确了 `/workpackage_schema` 与 `contracts/` 关系。
2. `tests/test_workpackage_blueprint_schema_versioning.py`
   - 校验 `skills` 为 v1 required 字段。
3. `tests/test_workpackage_schema_address_case_example.py`
   - 校验 sample 包含 `skills`，并可通过 v1 schema。
4. `tests/test_workpackage_schema_companion_artifacts.py`
   - 路径基线切换到 `workpackage_schema/`。

### 回归结果

1. `./.venv/bin/pytest -q tests/test_workpackage_v1_cleanup_guard.py tests/test_workpackage_blueprint_schema_versioning.py tests/test_workpackage_schema_address_case_example.py tests/test_workpackage_schema_companion_artifacts.py`
   - `13 passed`
2. `./scripts/check_workpackage_cleanup.sh`
   - `19 passed`

## 5) 仍建议后续推进（BM Master）

1. 清理 `output/` 与历史状态文档中对已删除 bundles 的“当前态引用”，统一打上 `legacy` 标签，避免误导。
2. 将“bundle 必须含 `workpackage.json + skills/`”增加到仓库卫生脚本，形成静态扫描硬门禁。
3. 对运行时加载逻辑补一条集成测试：验证 `workpackage.json.skills[].path` 与实际文件一致且可加载。

