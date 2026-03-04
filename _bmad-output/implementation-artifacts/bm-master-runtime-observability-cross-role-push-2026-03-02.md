# BM Master 汇总输入：运行态可观测下一阶段统一推进清单（2026-03-02）

## 1. 目标与范围

- 目标：在已通过 S2-14 MVP 验收基础上，完成运行态可观测从“可演示”到“可运营”的闭环落地。
- 范围：`OBS-RUNTIME-S2-5` ~ `OBS-RUNTIME-S2-9`，并补齐版本对比、基线固化、自动评估调度、分区归档与合规门禁。
- 约束：严格 `PG-only`、`No-Fallback`、测试先行（先失败用例再实现）。

## 2. BM Master 统一编排动作

1. 在 Linear 建立一个母 Epic：`Runtime Observability Full-Closure (Post-MVP)`。
2. 将以下 8 个推进项拆成独立 Issue，并按依赖关系排期。
3. 每个 Issue 强制包含：失败用例、实现、回归证据、验收链接（PR + 测试输出 + 文档更新）。
4. 每个 Issue 关联对应 Story 文档与 PR，禁止“代码已改但无 Story/无测试”的并入。

## 3. 跨角色推进项（可直接建单）

### P0-1 版本对比真实口径落地（替换占位实现）
- Owner：`A-DEV`（主）、`A-QA`（验收）
- 现状：`runtime_version_compare` 仍返回固定 0 差异。
- 实施：按 `ruleset_id/workpackage_version` 实算 `success_rate_delta/blocked_rate_delta/avg_confidence_delta`。
- 测试：新增 API 契约 + 数据集对照测试（正差异/负差异/空集）。
- DoD：页面版本对比不再恒为 0，且结果与 SQL 核对一致。

### P0-2 质量漂移基线固化任务
- Owner：`A-OBS`（主）、`A-DEV`（实现）
- 现状：`baseline_profile` 缺失时自动回退 candidate，存在漏报风险。
- 实施：新增“每日基线快照”任务；无基线时返回显式状态并告警，不可静默通过。
- 测试：基线存在/缺失/过期三类失败用例。
- DoD：`baseline_missing=false` 成为常态；缺基线告警可追溯。

### P0-3 告警自动评估调度化
- Owner：`A-OBS`（主）、`A-OPS`（调度）
- 现状：Reliability/Freshness/Drift/Performance 主要依赖手动 evaluate API。
- 实施：接入 worker 定时任务（5~15 分钟周期）自动触发评估。
- 测试：调度触发、抑制窗口、重复告警去重、ACK 审计链路。
- DoD：24h 内自动产生告警样本，ACK 后审计可查。

### P0-4 事件字段完整率门禁
- Owner：`A-OBS`（主）、`A-QA`（门禁）
- 实施：对 `trace_id/span_id/pipeline_stage/client_type/runtime_receipt_id` 增加完整率检测。
- 测试：构造缺字段样本验证告警和门禁阻断。
- DoD：CI 输出字段完整率报表；低于阈值阻断发布。

### P1-5 S2-8 分区与保留归档实装
- Owner：`A-ARCH`（设计）、`A-DEV`（落地）、`A-OPS`（运维）
- 现状：已有阈值与索引，但未形成分区/冷热归档执行闭环。
- 实施：Alembic 增加时间分区、归档作业、回查脚本。
- 测试：分区命中、归档回查、性能回归。
- DoD：首屏聚合 `<1.5s`、任务下钻 `<800ms`（本地基线）且有压测证据。

### P1-6 RBAC 与脱敏覆盖全下钻接口
- Owner：`A-SEC` 或 `A-DEV`（主）、`A-QA`（验收）
- 现状：S2-14 已覆盖部分链路，仍需覆盖 task detail/trace replay/export。
- 实施：viewer/oncall/admin 最小权限矩阵统一到所有 runtime 观测接口。
- 测试：越权访问、脱敏一致性、审计完整性。
- DoD：越权 100% 失败且错误语义一致；敏感字段无泄漏。

### P1-7 指标字典统一（业务KPI vs 工程SLI）
- Owner：`A-PM`（主）、`A-OBS`（共担）
- 实施：沉淀一份统一指标字典（名称、公式、分母规则、口径边界、数据源）。
- 测试：文档与 API 对账检查脚本。
- DoD：PRD/架构/API/页面四处口径一致，无前端私算核心指标。

### P1-8 真实流量可观测覆盖率日报
- Owner：`A-OBS`（主）、`A-OPS`（运营）
- 实施：新增日报产物（真实任务占比、链路闭环率、缺字段率、告警处理时效）。
- 测试：日报生成稳定性 + 指标阈值触发验证。
- DoD：连续 7 天可生成，支持值班巡检与周复盘。

## 4. 角色分工（BM Master 汇总视图）

- `A-OBS`：P0-2、P0-3、P0-4、P1-8 主责；提供阈值与巡检标准。
- `A-DEV`：P0-1、P1-5、P1-6 主实现；负责 API/Service/DAO 与迁移脚本。
- `A-QA`：所有 P0/P1 的失败用例先行与回归门禁编排。
- `A-ARCH`：P1-5 的分区/归档架构边界与演进路径评审。
- `A-PM`：P1-7 口径冻结，推动 Linear 依赖与验收节奏。
- `A-OPS`：P0-3 调度上线、P1-5 归档执行、P1-8 日报运营化。

## 5. 建议依赖顺序（避免互相阻塞）

1. 先做：P0-1、P0-2。
2. 再做：P0-3、P0-4。
3. 并行推进：P1-6、P1-7。
4. 最后收口：P1-5、P1-8。

## 6. 每个 Issue 的强制交付清单（模板）

1. 失败测试用例链接（先红后绿）。
2. 代码改动 PR 链接。
3. 运行命令与测试结果摘要。
4. 验收证据路径（`docs/acceptance/*.md|json` 或 `output/acceptance/*.json`）。
5. 回滚策略与风险说明。

## 7. 当前建议状态

- 建议 BM Master 将上述 8 项在 `2026-03-03` 前完成建单与负责人分配。
- 建议首批推进 P0 项（4 项）并在 `2026-03-05` 前完成第一次联调验收。
