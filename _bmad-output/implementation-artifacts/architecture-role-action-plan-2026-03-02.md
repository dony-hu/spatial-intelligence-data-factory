# A-ARC 跨角色推进清单（供 BM Master 汇总）

## 1. 文档目的

本清单用于 BM Master 汇总各角色待办并统一推进，聚焦“具体可执行事项”，不做纯状态数字复述。

## 2. 输入依据（产品与架构）

1. `docs/prd-spatial-intelligence-data-factory-2026-02-28.md`
2. `docs/architecture-spatial-intelligence-data-factory-2026-02-28.md`
3. `docs/architecture/architecture-runtime-observability-v2-2026-02-28.md`
4. `docs/sprint-planning-spatial-intelligence-data-factory-2026-02-27.md`
5. `docs/sprint-planning-runtime-observability-v2-2026-02-28.md`
6. `docs/bmm-workflow-status.yaml`
7. `docs/release-notes-2026-03-02.md`

## 3. 统一推进清单（按优先级）

| Priority | 推进事项 | 责任角色（主/协同） | 交付物 | 验收口径 | 建议 Workflow |
|---|---|---|---|---|---|
| P0 | 统一发布决策真相源（解决 gate/dashboard/release 口径漂移） | A-ARC / A-PM / A-QA | 决策口径对齐说明 + 同批次看板产物重算证据 | 同一批次在门禁、看板、发布说明三处结论一致 | `dev-story`（对应 S2-C3） |
| P0 | 完成架构收口 Epic 关闭前审计 | A-ARC / A-QA | 架构收口最终评审结论文档 | `epic-architecture-closure` 由“关闭前审计”转“可关闭” | `code-review` |
| P0 | 执行 Epic-1/Epic-2 retrospective 并形成下一轮约束 | A-SM / A-PM / A-ARC | retrospective 文档（每个 epic 一份） | 形成明确“保留项/删除项/硬约束”并进入下轮计划 | `retrospective` |
| P0 | 收尾 S2-14：真实链路驱动页面（非 seed 依赖） | A-DEV / A-QA / A-ARC | 验收证据（JSON+MD） | 不灌 seed 时可观测页面仍有 pipeline/llm 真实数据 | `dev-story`（S2-14 收尾） |
| P1 | 清理 `packages/factory_agent/agent.py` 迁移遗留死代码 | A-DEV / A-ARC | 代码清理提交 + 回归测试 | 无误导性旧路径，关键回归通过 | `create-story` -> `dev-story` |
| P1 | 落实 ARC-S6：Router→Service→Repository 分层收口 | A-ARC / A-DEV | service 层补全与 router 瘦身改造 | Router 不再承载业务编排逻辑 | `dev-story`（ARC-S6） |
| P1 | 落实 ARC-S1/ARC-S2：runtime 域实体化与物理表收口 | A-ARC / A-DEV / A-QA | migration + repository 切换证据 | 关键读写不再依赖兼容视图，发布/回放走 runtime 域实体 | `dev-story`（ARC-S1/S2） |
| P1 | 启动 S2-5/S2-6：SLI/SLO + 数据新鲜度观测 | A-DEV / A-QA / A-PM | API 与告警验证用例 | 可查询 SLI；`event_lag/data_age` 可见并可告警 | `create-story` -> `dev-story` |
| P1 | 启动 S2-9：最小 RBAC 与脱敏合规 | A-DEV / A-QA / A-ARC | 权限与脱敏测试证据 + 审计记录 | 未授权拒绝、敏感字段脱敏、审计可追踪 | `dev-story` |
| P1 | 将研发任务主追踪切换到 Linear（文件状态改镜像） | A-PM / A-SM / A-ARC | Linear issue 映射与执行约束文档 | 新任务在 Linear 创建并与 PR 关联；文件仅保留镜像 | 项目治理动作 |

## 4. BM Master 编排建议（执行顺序）

1. 先完成 4 个 P0 事项：
   - 决策口径统一
   - 架构收口审计关闭
   - 双 retrospective
   - S2-14 真实链路收尾
2. 再并行推进两条 P1 主线：
   - 架构收口线：ARC-S6 -> ARC-S1/S2
   - 观测运营线：S2-5/S2-6 -> S2-9
3. 最后推进治理收口：Linear 主追踪落地（文件状态降级为镜像）

## 5. 角色分发建议（可直接派单）

1. A-ARC：负责 P0-1、P0-2、P1-2、P1-3 的架构边界与验收门槛定义。
2. A-DEV：负责 P0-4、P1-1、P1-2、P1-3、P1-4、P1-5 的实现与回归。
3. A-QA：负责 P0-1、P0-2、P0-4、P1-4、P1-5 的契约与回归验收。
4. A-PM：负责 P0-1、P0-3、P1-6 的优先级与发布口径统一。
5. A-SM：负责 P0-3、P1-6 的节奏编排与跨角色阻塞清除。

## 6. 注意事项

1. 严格遵守 No-Fallback：关键依赖失败时必须阻塞，不允许 Dummy 或内存回退绕行。
2. 严格遵守测试先行：先失败用例 -> 再实现修复 -> 最后回归验证。
3. 严格遵守项目治理规则：研发任务进入 Linear，并与 PR 绑定。

