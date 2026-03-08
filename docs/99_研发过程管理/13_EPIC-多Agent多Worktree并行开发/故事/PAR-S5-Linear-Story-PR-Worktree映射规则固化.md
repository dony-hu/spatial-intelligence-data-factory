# Story 13.5（PAR-S5）：Linear / Story / PR / Worktree 映射规则固化

状态：ready-for-dev

说明：本 Story 对应 Epic13 的第 5 个实施故事，BMAD 数字化标识按 `13-5` 使用，当前 canonical 文件仍保留 `PAR-S5` 文件名。

## 用户故事

作为并行开发阶段的规划 / 集成编排 owner，
我希望把 Linear 任务、Story、分支、Worktree、PR 和 owner 的映射规则固化成一套统一口径，
以便任何一条并行工作流都能被追踪、回溯和交接，而不是出现“这条分支到底是谁、改什么、该通知谁”的管理盲区。

## 验收标准

1. 形成一份当前有效的映射规则说明，至少覆盖：
   - `Linear Issue / Story`
   - 仓库内 Story 文档
   - branch
   - Worktree
   - PR
   - owner
2. 明确每条并行工作流的最小绑定要求，至少能回答：
   - 缺哪个对象不能进入真实实现
   - 哪些字段必须在 PR 描述中显式出现
   - 哪些字段由集成值班和 `lane-06` 直接消费
3. 给出统一命名与登记口径，至少覆盖：
   - `codex/` 分支命名
   - Worktree 路径命名
   - Story 与 branch 的映射写法
   - PR 标题 / 描述中的必填项
4. 给出状态跟踪口径，至少区分：
   - `ready-for-dev`
   - `in-progress`
   - `done`
   - `blocked / follow-up`
5. 本 Story 的输出仅修改过程 / 规范文档，不伪造 Linear 编号、PR 编号或合并状态。
6. 交付结果能够被后续各 Lane、集成值班位和 `lane-06` gate 直接消费。

## 架构归属声明

- 所属面：`控制面`
- 允许依赖：
  - `AGENTS.md`
  - `docs/10_研发与工程规范/多Agent与多Worktree并行开发规范.md`
  - `docs/99_研发过程管理/文档分层索引.yaml`
  - `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/主题说明.md`
  - `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/冲刺计划.md`
  - `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/故事/PAR-S4-集成值班回归节奏与PR合并顺序固化.md`
- 禁止依赖：
  - 虚构 Linear 卡片编号或 PR 编号
  - 使用不带 `codex/` 前缀的分支命名作为正式建议
  - 在未绑定 owner / Worktree / branch 的情况下宣称某条 Lane 已进入实现
  - 用临时聊天结论替代可回填的主题正式文档
- 架构真相源：
  - `docs/02_总体架构/架构索引.md`
  - `docs/10_研发与工程规范/多Agent与多Worktree并行开发规范.md`
  - `docs/99_研发过程管理/文档分层索引.yaml`

## 任务拆分

- [ ] 任务 1：固化最小映射模型（AC: 1, 2）
  - [ ] 子任务 1.1：定义一条并行工作流的最小绑定对象集合
  - [ ] 子任务 1.2：说明缺失映射对象时的禁止动作
  - [ ] 子任务 1.3：区分 Epic 级后续项与 Story 级已完成项
- [ ] 任务 2：固化命名与登记规则（AC: 1, 3）
  - [ ] 子任务 2.1：定义 branch、Worktree 和 Story 的映射写法
  - [ ] 子任务 2.2：定义 PR 标题 / 描述的最小必填字段
  - [ ] 子任务 2.3：定义 owner 与受影响下游的登记口径
- [ ] 任务 3：固化状态跟踪口径（AC: 4, 6）
  - [ ] 子任务 3.1：定义 `ready-for-dev / in-progress / done / blocked / follow-up` 的使用边界
  - [ ] 子任务 3.2：说明 Story 状态、验收结论和 Epic 外部后续项的关系
  - [ ] 子任务 3.3：说明哪些状态可被集成值班和 `lane-06` gate 直接消费
- [ ] 任务 4：准备验收检查单（AC: 5, 6）
  - [ ] 子任务 4.1：形成最小人工验收清单
  - [ ] 子任务 4.2：列出仍需人工补齐的 Linear / PR 外部动作
  - [ ] 子任务 4.3：确保文档没有把缺失映射伪装成已完成事实

## 开发说明

- 本 Story 属于“流程映射与追踪收敛”类工作，不要求改业务代码。
- 本 Story 直接消费 `PAR-S4` 的 gate 结论与 PR 描述最小字段，不重新发明一版 PR 规范。
- 当前 Linear 仍为外部 blocker；本 Story 只能定义字段和映射规则，不能伪造卡片完成状态。
- 若后续决定把这套映射规则升级为 Ring1 工程规范，应由规划 / 集成编排位统一回填，不由执行 Lane 分散修改。

### 项目结构说明

- 正式过程文档落点：`docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/`
- 正式规范落点：`docs/10_研发与工程规范/`
- 正式入口文件：
  - `docs/00_阅读指南.md`
  - `docs/02_总体架构/架构索引.md`
  - `docs/99_研发过程管理/文档分层索引.yaml`
- 不应把本 Story 的核心结论写入：
  - `output/`
  - `logs/`
  - `_bmad-output/` 作为唯一正式版本
  - 业务代码目录

### 测试与验收约束

- 按 `AGENTS.md`，此类非代码变更若无法直接编写自动化用例，至少要提供最小人工验收检查单。
- 最小验收检查项建议包括：
  - 一条工作流是否真的能从 Story 追到 branch / Worktree / PR / owner
  - PR 字段是否足够支持集成值班与 `lane-06` gate
  - 状态口径是否区分 Story 完成和 Epic 外部后续项
  - 是否没有伪造 Linear / PR 已存在的事实

## 参考资料

1. `docs/10_研发与工程规范/多Agent与多Worktree并行开发规范.md`
2. `docs/99_研发过程管理/文档分层索引.yaml`
3. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/主题说明.md`
4. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/冲刺计划.md`
5. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/故事/PAR-S4-集成值班回归节奏与PR合并顺序固化.md`

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- 无

### Completion Notes List

- 已将 `13-5` 映射到当前 canonical Story `PAR-S5`。
- 已补齐所属面、允许依赖、禁止依赖、真相源、任务拆分和验收约束。
- 当前未更新 Linear，也未伪造 Sprint Tracking 条目。

### File List

- `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/故事/PAR-S5-Linear-Story-PR-Worktree映射规则固化.md`
