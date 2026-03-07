# 映射规则与 PR 必填字段

## 1. 目的

本文件用于把 Epic13 并行开发中的 `Linear / Story / branch / Worktree / PR / owner` 最小映射模型固化成一套统一口径。

它回答三件事：

1. 一条并行工作流至少要绑定哪些对象，才允许进入真实实现。
2. 这些对象应该如何命名、登记和回填。
3. 集成值班位与 `lane-06` 需要从 PR 中读取哪些字段，才能给出 gate 结论。

## 2. 最小映射模型

每条并行工作流至少绑定以下 6 个对象：

1. 一个 `Linear Issue / Story`
2. 一个仓库内 Story 文档
3. 一个 `codex/` 分支
4. 一个主仓外部的 Worktree
5. 一个 owner
6. 一个 PR

缺失规则：

1. 缺 `Linear`：允许进入“文档规划 / 外部 blocker”状态，不允许宣称管理链路已闭环。
2. 缺 Story 文档：不允许进入真实实现。
3. 缺 branch 或 Worktree：不允许进入并行实现。
4. 缺 owner：不允许进入集成窗口。
5. 缺 PR：不允许进入 `main` 合并流程。

## 3. 命名与登记规则

### 3.1 branch 命名

1. 执行 Lane 分支统一使用：
   - `codex/<lane>-<topic>`
2. Epic 内治理 / Story 分支可使用：
   - `codex/<epic>-<story>-<topic>`

当前实际示例：

| 类型 | 分支 |
| --- | --- |
| 规划位 | `codex/product-strategy-planning` |
| `lane-01` | `codex/lane-01-factory-agent` |
| `lane-02` | `codex/lane-02-runtime-api` |
| `lane-03` | `codex/lane-03-schema-contracts` |
| `lane-04` | `codex/lane-04-trust-hub-data` |
| `lane-05` | `codex/lane-05-frontend-workbench` |
| `lane-06` | `codex/lane-06-qa-integration` |
| `PAR-S3` Story 分支 | `codex/13-3-shared-contract-gates` |
| `PAR-S4` Story 分支 | `codex/13-4-integration-duty` |
| `PAR-S5` Story 分支 | `codex/13-5-mapping-rules` |

### 3.2 Worktree 路径命名

1. 执行 Lane Worktree：
   - `../spatial-intelligence-data-factory-worktrees/<nn>-<lane-topic>`
2. Story 级治理 Worktree：
   - `../spatial-intelligence-data-factory-worktrees/<epic>-par-s<story>-<topic>`

要求：

1. Worktree 必须在主仓外部。
2. 不允许把 Worktree 嵌套到主仓内部。
3. 每个 Worktree 单独维护 `.venv`、`.env.local` 和本地产物。

### 3.3 Story 标识写法

1. 仓库内 canonical Story 文件继续保留主题前缀，例如：
   - `PAR-S3`
   - `PAR-S4`
   - `PAR-S5`
2. BMAD / 数字化标识可附加在标题中，例如：
   - `Story 13.3（PAR-S3）`
   - `Story 13.4（PAR-S4）`
   - `Story 13.5（PAR-S5）`

## 4. PR 必填字段

每个进入集成窗口的 PR 描述至少包含：

1. `Linear`
   - 允许在本地 blocker 阶段写成 `TBD (external blocker)`，但不得伪造编号
2. `Story`
   - canonical Story 文件名或 Story ID
3. `Branch`
4. `Worktree`
5. `Owner`
6. `Owned Surface`
7. `Shared Contracts Impacted`
8. `Minimal Test Set`
9. `Downstream Lanes To Notify`
10. `lane-06 Gate`

推荐模板：

```md
## Mapping

- Linear: TBD (external blocker)
- Story: PAR-S5 / 13-5
- Branch: codex/13-5-mapping-rules
- Worktree: /Users/huda/Code/spatial-intelligence-data-factory-worktrees/13-par-s5-mapping-rules
- Owner: 规划 / 集成编排位

## Scope

- Owned Surface: docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/
- Shared Contracts Impacted: 无新增共享契约；复用 PAR-S3 / PAR-S4 口径
- Minimal Test Set: 人工验收检查单
- Downstream Lanes To Notify: lane-06
- lane-06 Gate: BLOCKED / PASS / NEEDS-FIX
```

## 5. 集成值班与 `lane-06` 直接消费字段

集成值班位最关心：

1. `Shared Contracts Impacted`
2. `Downstream Lanes To Notify`
3. `Owner`
4. `Branch / Worktree`

`lane-06` 最关心：

1. `Minimal Test Set`
2. `Shared Contracts Impacted`
3. `Downstream Lanes To Notify`
4. `lane-06 Gate`

若上述字段缺失，集成值班位或 `lane-06` 可直接判定 `BLOCKED`。

## 6. 状态跟踪口径

### 6.1 Story 状态

1. `ready-for-dev`
   - Story 已具备上下文，可进入独立 Worktree 执行。
2. `in-progress`
   - 已在独立 branch / Worktree 中实际推进，但交付物尚未收口。
3. `done`
   - Story 交付物已形成并通过当前 Story 级验收。

### 6.2 验收 / 外部后续项

1. `PASS`
   - 当前 Story 级交付物已可被下游消费。
2. `PARTIAL PASS`
   - 文档或入口已建立，但环境 / 依赖仍未完全就绪。
3. `BLOCKED`
   - 当前无法继续执行，需等待外部条件。
4. `FOLLOW-UP`
   - Epic 级或外部系统后续项，不应伪装成 Story 未完成。

使用原则：

1. Story 可 `done`，同时仍保留 Epic 级 `FOLLOW-UP`。
2. 不允许因为 Linear 或 TEA 缺失，就把已完成的文档类 Story 长期停在 `in-progress`。
3. 也不允许把 `FOLLOW-UP` 写成“已完成”。

## 7. 当前 Epic13 映射基线

| 工作流 | Story / 主题 | branch | Worktree | owner | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| 规划位 | Epic13 主题推进 | `codex/product-strategy-planning` | `/Users/huda/Code/worktrees/spatial-intelligence-data-factory-product-strategy` | 当前 Codex | 已启动 |
| `lane-01` | 工厂 Agent | `codex/lane-01-factory-agent` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/01-factory-agent` | `lane-01` owner | 已建 Worktree |
| `lane-02` | Runtime / API | `codex/lane-02-runtime-api` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/02-runtime-api` | `lane-02` owner | 已建 Worktree |
| `lane-03` | Schema / Contracts | `codex/lane-03-schema-contracts` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/03-schema-contracts` | `lane-03` owner | 已建 Worktree |
| `lane-04` | Trust Hub / Data | `codex/lane-04-trust-hub-data` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/04-trust-hub-data` | `lane-04` owner | 已建 Worktree |
| `lane-05` | Frontend | `codex/lane-05-frontend-workbench` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/05-frontend-workbench` | `lane-05` owner | 已建 Worktree |
| `lane-06` | QA / 集成门禁 | `codex/lane-06-qa-integration` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/06-qa-integration` | `lane-06` owner | baseline 已初始化，环境未完全就绪 |
| `PAR-S3` | 共享契约冻结 | `codex/13-3-shared-contract-gates` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/13-par-s3-contract-gates` | 规划 / 集成编排位 | Story 已完成，待 PR/merge |
| `PAR-S4` | 集成值班规则 | `codex/13-4-integration-duty` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/13-par-s4-integration-duty` | 规划 / 集成编排位 | Story 已完成，待 PR/merge |
| `PAR-S5` | 映射规则 | `codex/13-5-mapping-rules` | `/Users/huda/Code/spatial-intelligence-data-factory-worktrees/13-par-s5-mapping-rules` | 规划 / 集成编排位 | Story 进行中 |

## 8. 外部 blocker 的记录规则

以下对象允许写成外部 blocker，但不得伪造完成：

1. Linear 卡片编号
2. 实际 PR 编号
3. TEA skill 自动测试 / trace 产物
4. 尚未在当前 Worktree 初始化的本地 `.venv`

建议写法：

1. `TBD (external blocker)`
2. `FOLLOW-UP`
3. `not available locally`

禁止写法：

1. 编造 `LIN-123`
2. 编造 `PR #456`
3. 把没跑过的测试写成 `PASS`
