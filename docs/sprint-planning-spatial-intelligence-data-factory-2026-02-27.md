# Sprint Planning - 空间智能数据工厂（2026-02-27）

## 1. 规划信息

- 规划版本：v1.0
- 规划日期：2026-02-27
- 上游输入：
  - `docs/prd-spatial-intelligence-data-factory-2026-02-27.md`
  - `docs/architecture-spatial-intelligence-data-factory-2026-02-27.md`
- 规划目标：将 Implementation 阶段拆解为可执行 Story 与验收门禁。

## 2. Sprint 目标

1. Sprint-1：稳定治理主链路（任务状态、结果契约、人工审核闭环）。
2. Sprint-2：稳定质量门禁链路（P0/夜间门禁/看板证据一致性）。
3. Sprint-3：推进工程治理收敛（入口收敛、模块边界清晰化、环境可复现）。

## 3. Sprint-1 Backlog（P0）

| ID | Story | 目标 | 主要交付物 | 验收标准 |
|---|---|---|---|---|
| S1-A1 | 治理任务状态机稳定化 | 保证 `PENDING->RUNNING->SUCCEEDED/FAILED` 行为一致 | `services/governance_api/app/routers/tasks.py`、`services/governance_worker/app/jobs/governance_job.py` | 关键状态流转测试通过，异常路径可复现 |
| S1-A2 | 结果契约强校验 | 保证 `strategy/confidence/evidence` 必填且结构一致 | `services/governance_api/app/models/*`、`services/governance_api/tests/*` | 缺失字段时 API 返回明确错误语义 |
| S1-A3 | 人工审核闭环补齐 | 低置信度结果可进入审核并回写状态 | `services/governance_api/app/routers/manual_review.py`、`services/governance_api/tests/test_reviews_api.py` | 审核前后结果状态与审计字段一致 |

## 3.1 MVP 专项 Backlog（地址治理闭环，优先执行）

对应 Epic：`docs/epic-address-governance-mvp-2026-02-27.md`

| ID | Story | 目标 | 主要交付物 | 验收标准 |
|---|---|---|---|---|
| MVP-A1 | CLI-Agent-LLM 对话确认治理需求 | 打通 CLI->Agent->LLM 方案确认 | `scripts/factory_cli.py`、`packages/factory_cli/session.py`、`packages/factory_agent/agent.py` | 仅真实 LLM 成功返回结构化方案；失败即阻塞并上报人工确认 |
| MVP-A2 | 地址治理流程试运行 | 支持 dry run 并产出结果 | `packages/factory_agent/agent.py`、`workpackages/bundles/*` | dry run 成功/失败语义清晰；失败不降级，直接阻塞待确认 |
| MVP-A3 | 工作包发布到 Runtime | 发布代码+skills+元数据到治理 Runtime | `packages/factory_agent/agent.py`、`packages/governance_runtime/*` | Runtime 可识别并执行；发布阻塞需人工确认后再继续 |
| MVP-A4 | 地址治理流水线最小构建 | 跑通最小地址治理链路 | `packages/address_core/*`、`scripts/*` | 样例地址可产出治理结果；异常路径无 fallback |
| MVP-A5 | 可信数据 Hub 能力沉淀 | 积累外部 API 能力与可信互联网数据 | `packages/trust_hub/__init__.py`、`data/trust_hub.json` | 可注册/查询能力与样例数据；外部能力异常需阻塞确认 |
| MVP-A6 | 数据库模型与持久化闭环补齐 | 消除主链路与发布链路持久化断层 | `services/governance_api/app/repositories/*`、`packages/governance_runtime/*`、`database/*` | 任务/发布/LLM状态/TrustHub 均可持久化查询，并记录阻塞审批链路 |

## 4. Sprint-2 Backlog（P0/P1）

| ID | Story | 目标 | 主要交付物 | 验收标准 |
|---|---|---|---|---|
| S2-C1 | P0 门禁稳定性增强 | 确保核心工作包门禁可稳定阻断回归 | `.github/workflows/p0-workpackage.yml`、`scripts/run_p0_workpackage.py` | 关键失败用例可在 CI 稳定触发阻断 |
| S2-C2 | 夜间门禁失败分类完善 | 增强重试与失败归因可读性 | `scripts/run_nightly_quality_gate.py`、`output/workpackages/*.json` | 失败归类字段完整，告警信息可追踪 |
| S2-C3 | 看板与门禁证据对齐 | 确保看板数据与门禁产物一致 | `scripts/build_dashboard_data.py`、`web/dashboard/*` | 同一批次在看板与产物中结果一致 |

## 5. Sprint-3 Backlog（P1）

| ID | Story | 目标 | 主要交付物 | 验收标准 |
|---|---|---|---|---|
| S3-D1 | 运行入口收敛 | 明确标准启动路径，减少并行入口歧义 | `README.md`、启动脚本清单文档 | 新成员按文档可完成最小链路启动 |
| S3-D2 | 大模块拆分计划落地 | 降低单文件复杂度与回归风险 | 模块拆分设计 + 对应测试补齐 | 拆分前后关键行为一致，回归通过 |
| S3-D3 | 环境可复现治理 | 统一依赖与环境构建方式 | 依赖说明文档、环境初始化脚本 | 新环境可执行最小测试集 |

## 6. 迭代节奏建议

1. Week-1：完成 Sprint-1（主链路稳定）。
2. Week-2：完成 Sprint-2（门禁与看板闭环）。
3. Week-3：推进 Sprint-3（工程治理收敛）。

## 7. 测试与质量门禁策略

1. 每个 Story 必须先补失败用例，再实现修复，再执行验证。
2. P0 Story 合并前必须通过对应单测/集成测试与 CI 门禁。
3. 所有关键变更必须产出结构化证据（JSON/Markdown）。
4. MVP 地址治理链路启用 No-Fallback Gate：关键依赖失败必须 fail-fast，不允许降级通过。
5. 阻塞问题必须产出阻塞报告并进入人工确认队列，未确认不得继续执行后续阶段。

## 8. 风险与应对

1. 风险：多运行模式导致行为不一致。  
应对：引入默认模式并将运行态写入证据。

2. 风险：门禁失败噪音高影响迭代节奏。  
应对：失败分类标准化，区分暂态失败与真实回归。

3. 风险：工程治理任务被功能需求挤压。  
应对：在每个 Sprint 预留固定容量用于治理类 Story。
4. 风险：外部依赖（LLM/API）波动导致进度阻塞。  
应对：执行“阻塞即停”策略，统一由你确认处置方案，避免隐式绕行造成结果污染。

## 9. DoD（Sprint Planning 完成定义）

1. Backlog 已按 P0/P1 分级并具备验收标准。
2. 每个 Story 指定了主要交付物与验证方式。
3. 迭代节奏、风险和应对已明确。
4. 可直接进入 `create-story` 工作流拆解执行。
