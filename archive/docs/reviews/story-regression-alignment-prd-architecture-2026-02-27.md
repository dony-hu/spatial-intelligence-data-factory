# Story 全量回归对齐报告（PRD + 最新架构）- 2026-02-27

> 文档状态：历史归档
> 归档原因：一次性 Story 对齐回归报告，现已固化进 Story 模板和检查清单
> 归档日期：2026-03-06

## 1. 回归范围

1. PRD：`archive/docs/formal/product/prd-2026-02-27.md`
2. 架构：
- `docs/architecture/系统总览.md`
- `docs/architecture/模块边界.md`
- `docs/architecture/依赖关系.md`
3. Story：`docs/stories/*.md`（共 10 个）

## 2. 回归结论

结论：**全部 Story 已完成与 PRD/架构主线的结构化对齐**。

本轮对齐动作：

1. 为全部 Story 增加“对齐信息（PRD/架构）”。
2. 为全部 Story 增加“模块边界与 API 边界”。
3. 为全部 Story 增加“依赖与禁止耦合”约束。
4. 对 OBS-PG-S1 增加 MVP 最小量化阈值，消除仅定性 AC 的评审风险。

## 3. Story 对齐矩阵

1. `S1-A1`：对齐 EPIC A/B，补齐状态机边界与禁止耦合。
2. `S1-A2`：对齐 EPIC A/C，补齐结果契约边界与禁止耦合。
3. `S1-A3`：对齐 EPIC A/C，补齐人工审核 API 边界与审计约束。
4. `MVP-A1`：对齐 EPIC A/B，补齐 CLI-Agent-LLM 边界与 No-Fallback 约束。
5. `MVP-A2`：对齐 EPIC B/C，补齐 dryrun 执行边界与阻塞语义。
6. `MVP-A3`：对齐 EPIC B/C，补齐 publish-runtime 依赖与版本契约。
7. `MVP-A4`：对齐 EPIC A/C，补齐流水线输入输出边界与失败语义。
8. `MVP-A5`：对齐 EPIC A/B/D，补齐 Trust Hub 与 Core 去循环依赖约束。
9. `MVP-A6`：对齐 EPIC B/D，补齐多 schema + Alembic 唯一 DDL 约束。
10. `OBS-PG-S1`：对齐 EPIC C/D，补齐可观测 API 边界、依赖约束与量化阈值。

## 4. 关键新增约束（跨 Story 统一）

1. 仅 Repository/DAO 可访问 PG；CLI 不可直连数据库。
2. Core 不可依赖 Web Framework 对象。
3. 页面不可绕过 API 直连数据库。
4. 禁止用 fallback 掩盖关键失败；必须 `blocked/error`。
5. 生产 DDL 仅允许 Alembic 路径。

## 5. 已落地的评审修复

1. OBS-PG-S1 增加量化 AC：
- `snapshot` P95 <= 2s（1000 事件样本）
- 回放完整率 >= 99%

2. 所有 Story 已可映射到最新架构三文档，不再仅停留在业务目标描述。

## 6. 下一步建议（进入开发）

1. 按 `OBS-PG-S1-T1` 先补失败用例（字段契约缺失/不合规）。
2. 以该 Story 为模板，把新增 Story 默认模板固化为“目标 + AC + 对齐 + 边界 + 禁止耦合”。
3. 在后续 PRD 评审中直接引用本报告作为 Story 对齐基线。
