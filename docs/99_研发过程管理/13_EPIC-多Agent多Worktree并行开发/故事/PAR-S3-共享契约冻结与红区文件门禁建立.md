# Story 13.3（PAR-S3）：共享契约冻结与红区文件门禁建立

状态：done

说明：本 Story 对应 Epic13 的第 3 个实施故事，BMAD 数字化标识按 `13-3` 使用，当前 canonical 文件仍保留 `PAR-S3` 文件名。

## 用户故事

作为并行开发阶段的规划 / 集成编排 owner，
我希望在各 Lane 开始实现前冻结共享契约并建立红区文件门禁，
以便下游团队不会一边猜接口一边实现，最终把冲突集中到 `main` 合并阶段爆炸。

## 验收标准

1. 形成一份当前有效的共享契约清单，至少覆盖：
   - `AGENTS.md`
   - `docs/00_阅读指南.md`
   - `docs/02_总体架构/架构索引.md`
   - `docs/99_研发过程管理/文档分层索引.yaml`
   - `workpackage_schema/schemas/`
   - `migrations/versions/`
   - `services/governance_api/app/models/`
   - 跨域数据库 / API 契约
2. 每个共享契约对象都已明确唯一 owner，或明确“先契约 PR、后下游消费”的串行路径。
3. 红区文件列表与处理规则和正式规范保持一致，不再出现“默认谁都能改”的模糊口径。
4. 契约变更 PR 与实现 PR 的拆分规则已明确，至少能说明：
   - 什么改动必须单独提契约 PR
   - 什么改动允许在 Lane 内实现 PR 中完成
   - 合并前谁负责确认下游回归
5. 本 Story 的输出仅修改过程 / 规范文档，不把并行开发治理逻辑硬编码进运行时代码链路。
6. 交付结果能够被后续 `lane-03`、`lane-04`、`lane-06` 直接消费为执行前置条件。

## 架构归属声明

- 所属面：`控制面`
- 允许依赖：
  - `AGENTS.md`
  - `docs/10_研发与工程规范/多Agent与多Worktree并行开发规范.md`
  - `docs/10_研发与工程规范/版本管理策略.md`
  - `docs/10_研发与工程规范/项目目录结构.md`
  - `docs/99_研发过程管理/文档分层索引.yaml`
  - `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/主题说明.md`
  - `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/设计说明.md`
  - `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/冲刺计划.md`
- 禁止依赖：
  - 通过修改 `governance_worker`、`factory_agent`、`governance_api` 主链代码来表达并行治理规则
  - 把 `_bmad-output/`、`output/`、`logs/` 中的临时证据当作正式规则源
  - 在未先冻结契约的情况下，让多个 Lane 并发修改红区对象
  - 用伪造的 Linear 编号、占位 PR、虚构 owner 冒充治理完成
- 架构真相源：
  - `docs/02_总体架构/架构索引.md`
  - `docs/02_总体架构/系统总览.md`
  - `docs/02_总体架构/数据工厂技术架构.md`
  - `docs/02_总体架构/模块边界.md`
  - `docs/02_总体架构/依赖关系.md`
  - `docs/10_研发与工程规范/多Agent与多Worktree并行开发规范.md`

## 任务拆分

- [x] 任务 1：盘点共享契约与红区对象（AC: 1, 3）
  - [x] 子任务 1.1：从正式规范、AGENTS 和主题设计中提取共享契约对象全集
  - [x] 子任务 1.2：区分“唯一 owner 串行修改”和“先契约 PR 后下游实现”两种处理路径
  - [x] 子任务 1.3：补充当前规范未显式列出、但已在冲刺计划中列为红区的对象
- [x] 任务 2：固化 owner 与审批路径（AC: 2, 4）
  - [x] 子任务 2.1：为每个共享契约对象指定 owner 角色
  - [x] 子任务 2.2：定义契约 PR、实现 PR、回归确认三者的责任边界
  - [x] 子任务 2.3：明确“每日唯一共享契约 PR”与集成值班确认规则
- [x] 任务 3：回填 Epic13 过程文档（AC: 3, 4, 6）
  - [x] 子任务 3.1：将共享契约冻结清单回填到 Epic13 主题目录中的正式过程文档
  - [x] 子任务 3.2：确保后续 `PAR-S4`、`PAR-S5` 可直接引用本 Story 的结论
  - [x] 子任务 3.3：如影响 Ring1 正式规范，明确需要同步更新的正式文档入口
- [x] 任务 4：准备验收检查单（AC: 5, 6）
  - [x] 子任务 4.1：给出最小人工验收清单
  - [x] 子任务 4.2：列出下游消费方需要回归的点
  - [x] 子任务 4.3：标记仍受 Linear 外部 blocker 影响的环节

## 开发说明

- 本 Story 属于“治理与文档收敛”类工作，不要求改业务代码。
- 如果发现共享契约冻结需要修改 Ring1 正式规范，必须同步回填正式文档，而不是只写过程注释。
- 本 Story 的重点不是“列清单”本身，而是让后续 Lane 真正知道哪些对象不能自由并发修改。
- `PAR-S3` 的直接下游是：
  - `PAR-S4`：集成值班、回归节奏与 PR 合并顺序固化
  - `PAR-S5`：Linear / Story / PR / Worktree 映射规则固化
  - `lane-03`：共享契约冻结清单落地
- 当前 Linear 仍为外部 blocker；本 Story 不得伪造 Linear 卡片完成状态，只能记录待人工接入。
- 默认 `W-STW` 流水线中的 TEA 测试 / trace skill 当前未安装；本 Story 按仓库规则改走“最小人工验收检查单”收口，不把工具缺失伪装成测试通过。

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

- 按 `AGENTS.md`，此类非代码变更若无法直接编写自动化用例，至少要提供最小验收检查清单。
- 最小验收检查项建议包括：
  - 红区对象是否全部列全
  - 每个对象是否有唯一 owner 或契约 PR 路径
  - 是否明确了契约 PR 与实现 PR 的拆分规则
  - 是否说明了需要通知的下游 Lane
  - 是否避免把过程结论伪装成已执行完成的事实

## 参考资料

1. `docs/10_研发与工程规范/多Agent与多Worktree并行开发规范.md`
2. `docs/10_研发与工程规范/版本管理策略.md`
3. `docs/10_研发与工程规范/项目目录结构.md`
4. `docs/02_总体架构/模块边界.md`
5. `docs/02_总体架构/依赖关系.md`
6. `docs/99_研发过程管理/文档分层索引.yaml`
7. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/主题说明.md`
8. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/设计说明.md`
9. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/冲刺计划.md`
10. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/验收/启动检查清单.md`
11. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/共享契约冻结清单.md`
12. `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/验收/PAR-S3-验收检查单.md`

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- 无

### Completion Notes List

- 已将 `13-3` 映射到当前 canonical Story `PAR-S3`。
- 已补齐所属面、允许依赖、禁止依赖、真相源、任务拆分和验收约束。
- 当前未更新 Linear，也未伪造 Sprint Tracking 条目。
- 已形成 `共享契约冻结清单.md`，可直接作为 `lane-03`、`lane-04`、`lane-06` 的前置输入。
- 已形成 `PAR-S3-验收检查单.md`，并按文档类 Story 采用人工验收口径完成收口。
- Linear 建单、TEA skills 安装和 Epic13 sprint-status 基线仍为 Epic 级外部后续项，不阻塞本 Story 的文档交付完成。

### File List

- `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/故事/PAR-S3-共享契约冻结与红区文件门禁建立.md`
- `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/共享契约冻结清单.md`
- `docs/99_研发过程管理/13_EPIC-多Agent多Worktree并行开发/验收/PAR-S3-验收检查单.md`
