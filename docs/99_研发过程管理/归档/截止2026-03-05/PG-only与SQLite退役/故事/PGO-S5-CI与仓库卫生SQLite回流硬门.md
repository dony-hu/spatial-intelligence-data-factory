# Story: PGO-S5 CI与仓库卫生 SQLite 回流硬门

## 目标

在 CI 与本地检查中增加“运行主链路 SQLite 回流检测”，保证后续提交不再引入 SQLite 运行依赖。

## 验收标准

1. CI 新增检查：运行主链路路径出现 sqlite 关键字时阻断。
2. 本地提供一致检查命令（如 `make check-repo-hygiene` 扩展项）。
3. 报警输出包含文件路径与修复建议。

## 开发任务

1. 先补测试：构造 sqlite 回流样本应触发失败。
2. 再改实现：新增或扩展脚本与 workflow。
3. 最后回归：本地 + CI dry-run 验证。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC C、EPIC D。
2. 架构对齐：`docs/02_总体架构/模块边界.md`。

## 模块边界与 API 边界

1. 模块：`scripts/check_repo_hygiene.sh`、`.github/workflows/*`。
2. 边界：门禁只检查运行主链路目录，避免误伤 archive 历史内容。

## 依赖与禁止耦合

1. 允许：静态扫描 + 白名单目录策略。
2. 禁止：无白名单的全仓粗暴拦截导致历史资产不可维护。
