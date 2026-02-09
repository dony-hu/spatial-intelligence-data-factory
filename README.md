# Spatial-Intelligence Data Factory 项目管理仓库

本仓库用于存放多人、多 AI、多工具协作流程下的项目管理要求与执行日志。

## 范围

- 每日关键交付物追踪
- 成员维度工作日志
- 团队级日/周总结
- 跨工具机器可读格式（Markdown + YAML Front Matter + JSON Schema）
- 工具无关的项目要求与工具适配规范

## 目录结构

- `PROJECT_REQUIREMENTS.md`：工具无关的项目要求（`MUST/SHOULD/MAY`）。
- `PROJECT_MANAGEMENT_REQUIREMENTS.md`：项目管理策略与强制日志规则。
- `TOOLING_ADAPTERS.md`：将工具特定行为（如 Codex）映射到项目策略。
- `logs/daily/`：项目级每日记录（`YYYY-MM-DD.md`）。
- `logs/members/`：成员日志（`<member-id>/YYYY-MM-DD.md`）。
- `logs/summary/`：团队汇总（`weekly-YYYY-Www.md`、`monthly-YYYY-MM.md`）。
- `templates/`：可复用 Markdown 模板。
- `schemas/`：用于校验的 JSON Schema。

## 命名约定

- 日期格式：`YYYY-MM-DD`（ISO-8601）
- 周格式：`YYYY-Www`（ISO 周）
- 成员 ID：小写 kebab-case（例如：`li-ming`、`agent-codex`）

## 互操作约定

- 人类可读：Markdown
- AI/工具可读：YAML Front Matter + JSON Schema
- 所有日志都必须包含时区字段（`Asia/Shanghai`、`UTC` 等）
- 每条记录都必须包含可追溯的证据链接（PR、Issue、Commit、文档路径）

## 测试数据管理

- 目录入口：`testdata/README.md`
- 数据治理：`docs/testdata-governance.md`
- 清单注册：`testdata/catalog/catalog.yaml`
- 拉取脚本：`scripts/testdata/pull.sh <dataset-id>`
- 校验脚本：`scripts/testdata/verify.sh <dataset-id>`

示例：

```bash
scripts/testdata/pull.sh geo_poi_smoke_p0
scripts/testdata/verify.sh geo_poi_smoke_p0
```
