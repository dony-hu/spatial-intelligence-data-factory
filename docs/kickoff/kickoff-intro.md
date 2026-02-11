# 空间智能数据工厂项目开工会介绍（执行版）

## 1. 会议目标（本次必须达成）

1. 统一项目全景与分层边界（核心仓 vs 5 子仓）。
2. 统一 BMAD 执行方法（命令、阶段、产物、门禁）。
3. 确认角色责任、评审点、里程碑与近期动作。

## 2. 新人先看：项目全景

- 核心平台仓：`spatial-intelligence-data-factory`
- 子项目仓：上海、昆山、吴江、北京、宝安

边界规则：

1. 核心仓只沉淀可复用能力（至少 2 地区可复用）。
2. 子仓只承载本地定制，不反向污染平台范围。
3. 通过版本窗口接入核心能力，禁止复制核心代码。

## 3. BMAD 怎么执行（标准循环）

1. 先 ` /workflow-status` 看当前位置。
2. 执行推荐工作流（`/product-brief`、`/prd`、`/architecture` 等）。
3. 产物落仓并更新 `docs/bmm-workflow-status.yaml`。
4. 回到 ` /workflow-status` 进入下一轮。

## 4. 四阶段与必交付物

### 4.1 Analysis（`/product-brief`）

- 必交付：目标、范围边界、场景优先级、KPI、风险。
- 门禁：目标可量化、范围边界评审通过。

### 4.2 Planning（`/prd`、必要时 `/tech-spec`）

- 必交付：PRD、Epic->Story->Task、验收标准、优先级、排期。
- 门禁：每条需求可执行、可验收、有人负责。

### 4.3 Solutioning（`/architecture`）

- 必交付：架构方案、数据/API 契约、兼容/迁移/回滚方案。
- 门禁：架构评审通过、影响范围可追踪。

### 4.4 Implementation（`/sprint-planning`、`/create-story`、`/dev-story`、`/code-review`）

- 必交付：迭代计划、开发评审记录、测试证据、发布说明。
- 门禁：质量门禁通过、证据链完整。

## 5. 架构与治理图（会场讲解顺序）

1. BMAD 分层架构图（核心仓 + 5 子仓）
2. IPD 与 BMAD 对齐图（经营决策层 vs 交付执行层）
3. 混合治理图（角色 / Gate / 里程碑）

## 6. 当前状态（截至 2026-02-10 22:40 CST）

### 6.1 核心仓

- 当前阶段：Planning
- 当前工作流：`/prd`（进行中）
- HEAD：`ec1f183`

### 6.2 子仓 HEAD 快照

- 上海：`d2f0a10`
- 昆山：`70448bf`
- 吴江：`9ed02d4`
- 北京：`805ca83`
- 宝安：`427266f`

## 7. 行动闭环表（本周执行）

| 动作 | 责任角色 | 截止时间 | 验收标准 |
| --- | --- | --- | --- |
| 5 个子仓补齐 PRD v0.1 | 各子项目 PM | D+2 | 每仓有 In/Out Scope、Epic、>=3 条 Story、验收标准 |
| 跨项目 PRD 联评并升版 v1.0 | 平台 PM + Tech Lead | D+4 | 评审纪要、问题闭环清单、优先级冻结 |
| 冻结需求进入 `/architecture` | Project Owner | D+5 | 核心仓状态切到 Solutioning，架构评审议程已发布 |
| 明确 KPI 口径与基线 | PM + Compliance | D+5 | KPI 口径文档落仓并被各子仓引用 |
| 确认版本接入窗口 | Tech Lead + 子项目负责人 | D+5 | 发布窗口与回滚方案在周会纪要中确认 |

## 8. 资料与日志执行规范（必须）

1. 日报：`logs/daily/YYYY-MM-DD-姓名.md`
2. 周报：`logs/weekly/YYYY-Www-team.md`
3. 月报：`logs/monthly/YYYY-MM-team.md`
4. 共享资料：`docs/shared/*`，必须包含 `owner/updated_at/source/status`

## 9. 会后 24 小时内输出

1. 责任人名单（Owner/PM/Tech/Compliance）
2. PRD 联评会议纪要与 action items
3. 子仓补齐进度看板（红黄绿）
