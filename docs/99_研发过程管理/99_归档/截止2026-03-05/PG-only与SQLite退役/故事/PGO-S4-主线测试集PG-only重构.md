# Story: PGO-S4 主线测试集 PG-only 重构

## 目标

清理主线测试中对 SQLite 的硬依赖，建立 PG-only 的稳定回归集。

## 验收标准

1. 主线测试不再依赖 sqlite fixture。
2. 缺少 PG 依赖时测试明确 skip/fail-fast，而非隐式降级到 SQLite。
3. 输出新的主线测试基线报告。

## 开发任务

1. 先补/改测试：将 sqlite 断言改为 pg-only 断言。
2. 再改实现：补齐 PG fixture 与测试初始化。
3. 最后回归：主线 story 测试 + 验收脚本。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC C（质量门禁）。
2. 架构对齐：`docs/02_总体架构/系统总览.md`、`docs/02_总体架构/依赖关系.md`。

## 模块边界与 API 边界

1. 模块：`tests/`、`services/*/tests/`。
2. 边界：测试应验证生产口径（PG-only），不引入额外运行时真相源。

## 依赖与禁止耦合

1. 允许：测试使用 PG fixture / container。
2. 禁止：以 SQLite 作为“生产等价替代”继续验证主链路。
