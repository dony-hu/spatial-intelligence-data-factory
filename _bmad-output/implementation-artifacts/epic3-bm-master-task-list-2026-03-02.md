# Epic3（Runtime Observability V2）任务清单（供 BM Master 统一推进）

## 执行状态（更新：2026-03-02 12:45 +08:00）

| Task ID | 状态 |
|---|---|
| E3-T1 | done |
| E3-T2 | done |
| E3-T3 | done |
| E3-T4 | done |
| E3-T5 | done |
| E3-T6 | done |
| E3-T7 | done（本地映射清单已生成，待外部系统同步） |

## 1. 任务列表

| Task ID | 优先级 | 任务 | 主责角色 | 协同角色 | 交付物 | 验收标准 | 建议命令/Workflow |
|---|---|---|---|---|---|---|---|
| E3-T1 | P0 | 统一 Epic3 Story 状态口径（`done` vs `review`） | A-SM | A-DEV, A-QA | 状态对齐记录 + 更新后的 `sprint-status.yaml` | `3-5~3-9` 状态字段与 Story 工件一致，无冲突描述 | `code-review` |
| E3-T2 | P0 | 执行 Epic3 代码评审收口并形成结论 | A-QA | A-ARC, A-DEV | Epic3 review 报告（含阻塞/残余风险） | 无 P1/P0 未决问题，或有明确豁免与责任人 | `code-review` |
| E3-T3 | P0 | 更新 BMAD 工作流状态到“可关闭路径” | A-SM | A-PM | 更新 `docs/bmm-workflow-status.yaml` | `current_workflow` 不再指向 `dev-story`，推荐流转到关闭流程 | `workflow-status` |
| E3-T4 | P0 | 生成 Epic3 Full 验收汇总包（S2-1~S2-9 + S2-14） | A-QA | A-DEV, A-ARC | `docs/acceptance/epic3-full-acceptance-2026-03-02.json/md` | 覆盖所有 story、测试结果、风险与结论 | `dev-story` + `code-review` |
| E3-T5 | P1 | 补齐长期稳定性证据（多批次长压） | A-DEV | A-QA | 长压报告与事件覆盖率统计 | 覆盖率、字段完整率达到约定阈值并可复现 | `dev-story` |
| E3-T6 | P1 | 完成 Epic3 retrospective 并写入下一轮硬约束 | A-SM | A-PM, A-ARC | retrospective 文档 | 输出“保留项/删除项/硬约束/责任人” | `retrospective` |
| E3-T7 | P1 | 将 Epic3 任务映射到 Linear 并绑定 PR | A-PM | A-SM | Linear issue 清单 + PR 链接 | 新增/收口任务均在 Linear 可追踪 | 项目治理动作 |

## 2. 推荐执行顺序

`E3-T1 -> E3-T2 -> E3-T3 -> E3-T4 -> E3-T6`，`E3-T5/E3-T7` 并行推进。
