# Implementation Readiness Assessment Report

**Date:** 2026-03-03  
**Project:** spatial-intelligence-data-factory  
**Assessor:** A-ARC（Architecture）

## Document Discovery（Step-01 补充）

### 已纳入评估文档

1. PRD：`docs/prd-spatial-intelligence-data-factory-2026-02-28.md`
2. PRD（运行态可观测专项）：`docs/prd-runtime-observability-dashboard-2026-02-28.md`
3. Sprint/Stories：`docs/sprint-planning-spatial-intelligence-data-factory-2026-02-27.md` + `docs/stories/*.md`
4. Architecture：`_bmad-output/planning-artifacts/architecture.md`
5. UX：`_bmad-output/planning-artifacts/a-ux-审核闭环交互方案.md`

### 评估范围说明

本次实现就绪评估以 Epic3（Runtime Observability）与 S2-14/S2-15 闭环能力为主，兼顾上游工厂链路与工作包契约约束。

## PRD Analysis

### Functional Requirements

FR1: 提供运行总览能力，输出任务总数、完成率、阻塞率、平均置信度、待审核积压、最近处理时间。  
FR2: 提供风险分布能力，输出置信度分层、阻塞原因 Top5、低置信模式 Top5。  
FR3: 提供版本效果对比能力，支持 ruleset/workpackage 维度质量差异评估。  
FR4: 提供任务明细列表与筛选（状态、ruleset、时间窗、置信度）。  
FR5: 支持单任务下钻，查看输入、标准化结果、strategy、evidence、审核记录与 trace 回放入口。  
FR6: 提供新增治理包链路总览 API（pipeline）并输出阶段统计与成功率。  
FR7: 提供治理包事件时间线 API（events），输出 trace/span/source/event/status/payload 摘要。  
FR8: 提供 LLM 交互观测 API（interactions），输出模型、时延、token、失败原因与样本摘要。  
FR9: 支持统一筛选维度：window/ruleset/workpackage_id/version/status/confidence/client_type/pipeline_stage。  
FR10: 提供完整链路阶段可观测：`created -> llm_confirmed -> packaged -> dryrun_finished -> publish_confirmed -> submitted -> accepted -> running -> finished`。  
FR11: 提供链路时延分解（CLI、Agent、LLM、Runtime、端到端）及分位值。  
FR12: 提供节点成功率（CLI、LLM、Runtime、E2E）。  
FR13: `upload-batch` 支持 `workpackage_id+version` 执行，并对缺参/冲突返回 `INVALID_PAYLOAD`。  
FR14: 门禁动作必须生效：`confirm_generate` 与 `confirm_publish` 缺失即阻断。  
FR15: dry-run 报告必须完整输出 `records[] + spatial_graph` 且满足结构约束。  
FR16: 事件输出需包含中文可读字段（`source_zh/event_type_zh/status_zh/description_zh/pipeline_stage_zh`）。  
FR17: 权限与合规：viewer 脱敏、oncall/admin 全量轨迹、确认动作审计字段完整。  
FR18: 无数据时提供空态引导，支持样例灌入使页面可观测。  
FR19: 运行态页面默认以业务运行数据为真相源，不依赖研发看板文件。  
FR20: 任一工作包可展示 Runtime receipt 并形成可追溯闭环证据链。

Total FRs: 20

### Non-Functional Requirements

NFR1: No-Fallback/No-Mock，关键依赖失败必须 `blocked/error`。  
NFR2: PG-only 持久化主路径，Alembic 为唯一 DDL 演进入口。  
NFR3: 全链路审计可追溯（actor/action/reason/timestamp/trace_id/workpackage/version）。  
NFR4: 指标口径统一且可解释，避免前端自行计算核心指标。  
NFR5: 数据脱敏默认开启，权限差异可验证。  
NFR6: API 在数据不足时返回空结构，不返回 500。  
NFR7: 运行态页面与 API 查询同源，证据可复核。  
NFR8: 测试先行（TDD）并保持 E2E/集成/单元配比目标（2:6:2）。  
NFR9: 兼容层（旧 lab）不影响主验收口径。  
NFR10: 错误语义标准化（`INVALID_PAYLOAD`/`WORKPACKAGE_GATE_BLOCKED` 等）。  
NFR11: UI 可测性稳定（`data-testid` 约束）。  
NFR12: 工程资产可被 BM Master 聚合消费（implementation artifacts 可追溯）。

Total NFRs: 12

### Additional Requirements

1. `workpackage_schema` 作为项目一级目录协议入口，`skills` 为工作包组成部分。  
2. 不考虑旧版 workpackage，历史 bundle 已清理并迁移到新契约。  
3. 新任务追踪系统以 Linear 为准，文档资产用于验收与架构治理。

### PRD Completeness Assessment

1. 运行态专项 PRD 完整度高，接口与验收口径可执行。  
2. 全局 PRD（工厂总体）为战略级描述，需通过 stories 细化到可测 AC。  
3. Epic3 与 S2-15 已能承接主要运行态需求，但存在“阶段枚举口径漂移”和“证据路径命名漂移”。

## Epic Coverage Validation

### Coverage Matrix

| FR | Requirement | Epic/Story Coverage | Status |
|---|---|---|---|
| FR1 | 运行总览指标 | S2-1 | ✓ Covered |
| FR2 | 风险分布 | S2-1/S2-2 | ✓ Covered |
| FR3 | 版本效果对比 | S2-1/S2-7 | ✓ Covered |
| FR4 | 任务明细筛选 | S2-1/S2-2 | ✓ Covered |
| FR5 | 任务下钻与追溯 | S2-4 | ✓ Covered |
| FR6 | workpackage pipeline API | S2-14 | ✓ Covered |
| FR7 | workpackage events API | S2-14 | ✓ Covered |
| FR8 | LLM interactions API | S2-14/S2-9 | ✓ Covered |
| FR9 | 统一筛选维度 | S2-14/S2-2 | ✓ Covered |
| FR10 | 完整阶段链路含 dryrun/publish_confirmed | S2-14 + S2-15 | ⚠ Partial |
| FR11 | 时延分解与分位 | S2-14/S2-6 | ✓ Covered |
| FR12 | 节点成功率 | S2-14 | ✓ Covered |
| FR13 | upload-batch workpackage 执行与冲突校验 | S2-15 + `test_runtime_upload_batch.py` | ✓ Covered |
| FR14 | confirm_generate/confirm_publish 门禁 | S2-15 + `test_runtime_upload_batch.py` | ✓ Covered |
| FR15 | dry-run `records+spatial_graph` 完整性 | S2-15 + `test_runtime_upload_batch.py` | ✓ Covered |
| FR16 | 中文可读字段 | S2-15 + `test_runtime_workpackage_events_api_contract.py` | ✓ Covered |
| FR17 | RBAC 脱敏与审计 | S2-9 + `test_runtime_workpackage_observability_rbac.py` | ✓ Covered |
| FR18 | 样例灌入与空态引导 | S2-3 | ✓ Covered |
| FR19 | 运行态真相源替代研发看板 | S2-1/S2-2/S2-10 | ✓ Covered |
| FR20 | receipt 证据链闭环 | S2-14/S2-15 | ⚠ Partial |

### Missing Requirements

无完全缺失 FR；存在 2 项部分覆盖与 2 项实施证据风险：

1. FR10（阶段链路）部分覆盖
- Impact: S2-14 与 S2-15 阶段枚举不一致，回归与看板口径可能分裂。  
- Recommendation: 统一阶段枚举字典，测试与页面同源引用。

2. FR20（receipt 闭环）部分覆盖
- Impact: 文档层已定义，环境层未形成稳定可执行证据时，收口结论不可复现。  
- Recommendation: 将 DB baseline + 关键契约测试作为发布前置门禁。

3. 证据路径漂移（命名）
- Impact: 历史文档引用 `test_runtime_workpackage_events_zh_e2e.py`，仓库当前无此文件；自动化追溯会断链。  
- Recommendation: 统一改为现行测试文件并回填证据索引。

4. 执行环境阻塞
- Impact: 本地核心契约测试未通过（8 failed, 2 passed），阻塞验收。  
- Recommendation: 先修复 PG 基线与迁移一致性，再重新跑验收矩阵。

### Coverage Statistics

- Total PRD FRs: 20
- FRs fully covered: 18
- FRs partially covered: 2
- Coverage percentage (full): 90%

## UX Alignment Assessment

### UX Document Status

Found: `_bmad-output/planning-artifacts/a-ux-审核闭环交互方案.md`

### Alignment Issues

1. UX 案件状态机（`NEW/IN_REVIEW/.../CLOSED`）与运行链路阶段（`created/.../finished`）缺少映射表。  
2. UX 定义的“SLA 预警、批量操作二次确认”在 S2-14/S2-15 验收条目中未显式落到测试断言。  
3. UX 角色（审核员/组长/策略管理员/审计角色）与运行态角色（viewer/oncall/admin）需要一份权限映射矩阵。

### Warnings

1. 若不补齐状态与角色映射，后续 UI/API 可能出现“同名不同义”与验收口径争议。  
2. S2-15 Web E2E 已引入 `data-testid` 约束，这是正向项，应作为后续页面迭代的强约束保留。

## Epic Quality Review

### Critical Violations

1. 可执行证据与“已完成”状态冲突。  
- 现状：`sprint-status.yaml` 将 Epic3 标记为 `done`。  
- 证据：本地运行关键契约测试结果 `8 failed, 2 passed`，主要报错为 `relation governance.observation_event does not exist`。  
- 结论：当前更接近“文档完成，环境未就绪”。

### Major Issues

1. 阶段枚举存在前后版本漂移（S2-14 vs S2-15）。  
2. 一部分 Story 偏工程治理表述（技术里程碑导向），用户价值描述不够直接。  
3. 多数 Story AC 未采用 Given/When/Then，异常路径覆盖仍靠补充解释而非 AC 本体。  
4. 测试分层配比（E2E:集成:单元=2:6:2）尚未在 Epic3 层形成量化执行清单。

### Minor Concerns

1. 旧测试文件名在历史报告中仍被引用。  
2. 个别 Story 的“依赖”描述未显式注明阻塞等级与替代处置规则。

## Summary and Recommendations

### Overall Readiness Status

**NEEDS WORK**

### Critical Issues Requiring Immediate Action

1. PG 基线未初始化到可验收状态（数据库无业务表；关键契约测试失败）。  
2. 阶段枚举字典未统一（S2-14 与 S2-15 口径不同）。  
3. 证据路径存在命名漂移（历史引用测试文件不存在）。

### Recommended Next Steps（可直接派发 BM Master）

1. `IR-P0-01`：建立可复现实验收 DB 基线（`DATABASE_URL` 统一 + `alembic upgrade head` + smoke SQL）。Owner: A-DEV。  
2. `IR-P0-02`：重跑 Epic3 核心验收测试并固化报告（pipeline/events/llm/rbac/upload-batch + Web E2E）。Owner: A-QA。  
3. `IR-P0-03`：统一运行阶段枚举字典（含 `dryrun_finished/publish_confirmed`）并更新 API/UI/测试。Owner: A-ARC + A-DEV。  
4. `IR-P0-04`：修正文档中的旧测试路径引用，生成一份“证据索引映射表”。Owner: A-PM。  
5. `IR-P1-05`：补齐 UX 状态机与运行阶段、角色权限的映射文档并落测试断言。Owner: A-UX + A-ARC + A-QA。  
6. `IR-P1-06`：按 2:6:2 输出 Epic3 测试分层清单（E2E/集成/单元）并纳入 CI 报告。Owner: A-QA。  
7. `IR-P1-07`：固化 `implementation-readiness` 一键命令/workflow（输出到 `_bmad-output/implementation-artifacts`）。Owner: BM Master + A-DEV。  
8. `IR-P1-08`：Linear 建单并绑定 PR/证据路径，完成 Go/No-Go 会签前置。Owner: A-PM。

### Final Note

本次评估识别出 8 项关键问题（3 项 P0，5 项 P1）。在 `IR-P0-01~IR-P0-04` 完成并复测通过前，不建议执行 Epic3 最终完成态会签。
