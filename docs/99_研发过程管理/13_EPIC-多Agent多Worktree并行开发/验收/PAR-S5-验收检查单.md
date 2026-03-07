# PAR-S5 验收检查单

## 1. 结论口径

- 当前结论：`PASS`
- 含义：`PAR-S5` 的映射规则、PR 必填字段和状态跟踪口径已经形成，可直接供各 Lane、集成值班位和 `lane-06` gate 使用；Linear 建单与真实 PR 编号仍是外部后续项，但不阻塞本 Story 验收。

## 2. 验收项

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 是否定义最小映射模型 | `PASS` | 已明确 `Linear / Story / branch / Worktree / PR / owner` 六元绑定。 |
| 是否定义 branch / Worktree / Story 命名规则 | `PASS` | 已明确 `codex/` 前缀、主仓外部 Worktree 和 Story 标识写法。 |
| 是否定义 PR 必填字段 | `PASS` | 已给出字段清单和推荐模板。 |
| 是否定义状态跟踪口径 | `PASS` | 已区分 `ready-for-dev / in-progress / done / PASS / PARTIAL PASS / BLOCKED / FOLLOW-UP`。 |
| 是否给出现有 Epic13 的真实映射基线 | `PASS` | 已列出规划位、6 条 Lane 和 `PAR-S3`~`PAR-S5` 的当前映射。 |
| 是否区分 Story 已完成与 Epic 外部后续项 | `PASS` | 已明确 Story 可 `done`，同时保留 `FOLLOW-UP`。 |
| 是否已补齐 Linear Epic / Story 绑定 | `FOLLOW-UP` | 当前无本地 Linear 接入能力，需人工补齐。 |
| 是否已形成真实 PR 编号 | `FOLLOW-UP` | 当前仅完成文档与 Worktree 层推进，尚未实际提交 PR。 |

## 3. 人工验收动作

1. 核对模板中没有伪造 Linear 或 PR 编号。
2. 核对 branch 命名全部使用 `codex/` 前缀。
3. 核对 `lane-06` 直接消费字段与 baseline 文档一致。
4. 核对 Story 状态和外部后续项没有混写成一个结论。
5. 核对当前 Epic13 的映射基线与实际 `git worktree list` 一致。

## 4. Epic 级外部后续项

1. Linear 侧未建立 Epic13 及 `PAR-S1` 到 `PAR-S5` 对应卡片。
2. `PAR-S3`、`PAR-S4`、`PAR-S5` 当前仍停留在 Worktree / 分支阶段，尚未形成真实 PR 编号。
3. TEA 相关 skill 未安装，默认 `W-STW` 自动 ATDD / trace 步骤无法闭环。

## 5. 建议后续动作

1. 由人工在 Linear 中补齐 Epic13 与对应 Story 卡片。
2. 以本文件中的模板为准，给 `PAR-S3`、`PAR-S4`、`PAR-S5` 生成首批 PR 描述。
3. 等 `lane-06` 环境就绪后，再让 gate 结论进入真实 PR 流程。
