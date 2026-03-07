# PAR-S4 验收检查单

## 1. 结论口径

- 当前结论：`PASS`
- 含义：`PAR-S4` 的文档交付物已经齐备，集成值班职责、每日节奏、合并顺序和失败恢复路径已形成当前可执行基线；`lane-06` baseline、Linear 和外部 TEA 仍是 Epic 级后续项，但不阻塞本 Story 验收。

## 2. 验收项

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 是否形成唯一的集成值班角色与责任边界 | `PASS` | 已明确值班位、Lane owner、契约 owner、`lane-06` 与 PR 作者的分工。 |
| 是否给出每日节奏与窗口顺序 | `PASS` | 已给出共享契约确认、自测收口、交叉回归、合并窗口的顺序和建议时刻。 |
| 是否明确首轮启动期的合并顺序 | `PASS` | 已明确共享契约优先、后端 / 数据先于前端、`lane-06` 负责 gate。 |
| 是否明确失败停线与恢复规则 | `PASS` | 已说明暂停条件、回源修复路径和已合并后的 revert 原则。 |
| 是否给出 `lane-06` 的直接输入要求 | `PASS` | 已明确 smoke 集、已知失败清单、验证入口和影响列表。 |
| 是否与 `PAR-S3` 的共享契约规则保持一致 | `PASS` | 已直接复用共享契约冻结清单，不重新发明 owner 口径。 |
| `lane-06` baseline 是否已经实际产出 | `FOLLOW-UP` | 本 Story 已定义接口和节奏位置，但 baseline 文档仍需后续单独产出。 |
| 是否已补齐 Linear Epic / Story 绑定 | `FOLLOW-UP` | 当前无本地 Linear 接入能力，需人工在 Epic 层补齐。 |
| 是否已完成外部流水线测试与 trace | `FOLLOW-UP` | 当前未安装 `bmad-tea-testarch-atdd` / `bmad-tea-testarch-trace`，本 Story 改用人工验收检查单收口。 |

## 3. 人工验收动作

1. 核对“每日唯一共享契约 PR”规则是否与 `PAR-S3` 完全一致。
2. 核对 `lane-06` 在流程中承担 gate，而不是承担业务实现 owner。
3. 核对合并顺序没有允许 `lane-05` 在接口未稳定前提前入场。
4. 核对失败恢复要求回到原始 Lane / Worktree 修复，而不是直接在 `main` 绕过门禁。
5. 核对文档没有宣称 Linear 已建单，也没有伪造自动回归通过。

## 4. Epic 级外部后续项

1. `lane-06` baseline、已知失败清单和统一验证入口文档尚未单独产出。
2. Linear 侧未建立 Epic13 及 `PAR-S4` 对应卡片。
3. 外部 Skill 流水线依赖的 TEA 能力未安装，无法按默认步骤生成 ATDD 与 trace 产物。

## 5. 建议后续动作

1. 让 `lane-06` 依据本 Story 产出 baseline、已知失败清单和统一验证入口。
2. 让 `PAR-S5` 直接复用本 Story 中的 PR 字段和 gate 结论口径。
3. 由人工补齐 Linear Epic / Story。
