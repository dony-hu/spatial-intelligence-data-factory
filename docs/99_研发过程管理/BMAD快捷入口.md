# BMAD / SpecKit 指令与工作流缩略语速查表（中英）

本文用于统一 Codex 场景下 BMAD 的调用口令，便于快速触发。

规范定位：本文件是仓库内 BMAD `A-` 角色缩写映射的正式规范来源（canonical source）。

## 1. 缩略语规则

- 前缀约定：
  - `C-`：BMAD CLI 命令（终端命令）
  - `W-`：BMAD 工作流（Workflow）
  - `S-`：SpecKit 指令（Feature 规格流）
  - `A-`：BMAD 角色（Agent）
  - `T-`：BMAD 辅助任务（Task）
- 推荐触发句式：
  - 中文：`执行 W-ARC`
  - 英文：`Run W-ARC`

## 2. CLI 命令（C-）

| 原命令 | 英文缩写 | 中文缩写 | 用法示例 |
| --- | --- | --- | --- |
| `bmad install` | `C-INS` | `C-安装` | `执行 C-INS` |
| `bmad status` | `C-STS` | `C-状态` | `执行 C-STS` |
| `bmad uninstall` | `C-UNS` | `C-卸载` | `执行 C-UNS` |
| `bmad help` | `C-HLP` | `C-帮助` | `执行 C-HLP` |

## 3. 核心工作流（W-）

| 工作流 | 英文缩写 | 中文缩写 | 说明 |
| --- | --- | --- | --- |
| create-product-brief | `W-BRF` | `W-产品简报` | 产出产品简报 |
| create-prd | `W-PRD` | `W-需求文档` | 产出需求文档 |
| validate-prd | `W-VPRD` | `W-验证需求` | 校验需求质量 |
| edit-prd | `W-EPRD` | `W-修订需求` | 修订需求文档 |
| create-ux-design | `W-UXD` | `W-体验设计` | 产出 UX 设计 |
| create-architecture | `W-ARC` | `W-架构设计` | 产出架构方案 |
| create-epics-and-stories | `W-EPS` | `W-主题拆分` | 拆分研发主题与故事 |
| sprint-planning | `W-SPLN` | `W-冲刺规划` | 冲刺规划 |
| create-story | `W-STR` | `W-创建故事` | 创建故事 |
| dev-story | `W-DEV` | `W-故事开发` | 按故事开发 |
| code-review | `W-CR` | `W-代码评审` | 代码评审 |
| check-implementation-readiness | `W-RDY` | `W-实施就绪` | 实施前检查 |
| retrospective | `W-RET` | `W-冲刺复盘` | 冲刺复盘 |
| correct-course | `W-CC` | `W-方案纠偏` | 纠偏与重排 |
| sprint-status | `W-SSTS` | `W-冲刺进展` | 查看冲刺状态 |

## 4. 扩展工作流（W-）

| 工作流                          | 英文缩写     | 中文缩写      | 说明                                    |
| ---------------------------- | -------- | --------- | ------------------------------------- |
| quick-spec                   | `W-QSP`  | `W-快速方案`  | 快速规格化                                 |
| quick-dev                    | `W-QDV`  | `W-快速开发`  | 快速开发路径                                |
| domain-research              | `W-DRS`  | `W-领域研究`  | 领域研究                                  |
| market-research              | `W-MRS`  | `W-市场研究`  | 市场研究                                  |
| technical-research           | `W-TRS`  | `W-技术研究`  | 技术研究                                  |
| generate-project-context     | `W-GCTX` | `W-项目上下文` | 生成项目上下文                               |
| document-project             | `W-DOC`  | `W-项目文档`  | 项目文档化                                 |
| qa-generate-e2e-tests        | `W-E2E`  | `W-端到端测`  | 生成 E2E 测试                             |
| bmad-story-pipeline          | `W-STP`  | `W-故事流水线` | 在当前分支上执行单 Story 可配置流水线，不做 Worktree 隔离 |
| bmad-story-pipeline-worktree | `W-STW`  | `W-故事工作树` | 在隔离 Worktree 中执行单 Story 流水线并通过后合并     |
| bmad-epic-pipeline-worktree  | `W-EPW`  | `W-史诗工作树` | 在隔离 Worktree 中顺序交付整个 Epic 的未完成 Story  |

## 5. SpecKit 指令（S-）

| 指令 | 英文缩写 | 中文缩写 | 说明 |
| --- | --- | --- | --- |
| `/speckit.specify` | `S-SPC` | `S-规格定义` | 生成/更新 feature 规格（spec） |
| `/speckit.clarify` | `S-CLF` | `S-规格澄清` | 消歧与决策冻结 |
| `/speckit.plan` | `S-PLN` | `S-实现规划` | 生成实现计划（plan） |
| `/speckit.tasks` | `S-TSK` | `S-任务拆解` | 生成任务列表（tasks） |
| `/speckit.implement` | `S-IMP` | `S-任务实施` | 按任务落地实现 |
| `/speckit.analyze` | `S-ANL` | `S-一致性分析` | 对齐/回归一致性分析 |
| `/speckit.checklist` | `S-CHK` | `S-验收清单` | 生成验收清单 |
| `/speckit.taskstoissues` | `S-T2I` | `S-任务建单` | 将 tasks 转换为 issue |
| `/speckit.constitution` | `S-CST` | `S-宪章更新` | 更新 `.specify/memory/constitution.md` |

## 6. Agent 角色（A-）

| Agent Skill | 英文缩写 | 中文缩写 | 使用建议 |
| --- | --- | --- | --- |
| bmad-agent-bmad-master | `A-BMAD` | `A-总控` | 流程总控与路由 |
| bmad-agent-bmm-analyst | `A-ANL` | `A-分析师` | 需求分析与澄清 |
| bmad-agent-bmm-pm | `A-PM` | `A-产品经理` | PRD 组织与收敛 |
| bmad-agent-bmm-architect | `A-ARC` | `A-架构师` | 架构决策与约束 |
| bmad-agent-bmm-ux-designer | `A-UX` | `A-体验设计` | 交互与体验设计 |
| bmad-agent-bmm-dev | `A-DEV` | `A-开发工程` | 研发实现 |
| bmad-agent-bmm-qa | `A-QA` | `A-测试工程` | 测试策略与质量门 |
| bmad-agent-bmm-sm | `A-SM` | `A-敏捷教练` | 冲刺节奏与拆解 |
| bmad-agent-bmm-tech-writer | `A-TW` | `A-技术写作` | 技术文档产出 |
| bmad-agent-bmm-quick-flow-solo-dev | `A-SOLO` | `A-单人快开` | 单人快速推进 |

## 7. 辅助任务（T-）

| 任务 | 英文缩写 | 中文缩写 | 说明 |
| --- | --- | --- | --- |
| bmad-help | `T-HLP` | `T-流程导航` | 下一步推荐 |
| bmad-index-docs | `T-IDX` | `T-文档索引` | 文档索引 |
| bmad-shard-doc | `T-SHD` | `T-文档分片` | 大文档分片 |

## 8. 推荐触发模板

- 单步执行：
  - `执行 W-ARC`
  - `Run W-ARC`
  - `执行 S-PLN`
  - `执行 W-STP 13-1`
  - `执行 W-STW 13-1`
  - `执行 W-EPW 13`
- 角色 + 工作流：
  - `执行 A-ARC + W-ARC`
  - `Run A-PM then W-PRD`
- 串联执行：
  - `先 W-PRD 再 W-ARC`
  - `After W-PRD, run W-ARC`
  - `先 S-SPC 再 S-CLF 再 S-PLN`

## 9. 重要说明

- `bmad` CLI 目前只提供安装和状态类命令（如 `install/status/help`），不直接提供 `architect` 这类 workflow 子命令。
- 在 Codex 内触发工作流，建议使用自然语言或本表缩写（如 `W-ARC`）进行调用。
- SpecKit 指令清单以 `.codex/prompts/speckit.*.md` 为准，本表仅提供快捷缩写映射。
- 已安装外部工作树流水线 Skill：
  - `W-STP` -> `/bmad-story-pipeline`
  - `W-STW` -> `/bmad-story-pipeline-worktree`
  - `W-EPW` -> `/bmad-epic-pipeline-worktree`
- `W-STP` 运行在当前分支，不提供 Worktree 隔离；需要隔离时优先使用 `W-STW` 或 `W-EPW`。
- `W-EPW`、`W-STW`、`W-STP` 属于外部扩展 Skill，不替代仓库内 `codex/` 分支前缀、Linear 绑定和红区治理规则。

## 10. 固化到 Skill 的方案（已落地）

已新增项目内路由 Skill：

- [bmad-shortcuts-router](/Users/huda/Code/spatial-intelligence-data-factory/.agents/skills/bmad-shortcuts-router/SKILL.md)

### 10.1 使用方式

- 在 Codex 对话中直接输入缩写：
  - `执行 W-ARC`
  - `执行 A-ARC + W-ARC`
  - `执行 C-STS`
  - `执行 S-PLN`
  - `执行 W-STP 13-1`
  - `执行 W-STW 13-1`
  - `执行 W-EPW 13`
- 路由 Skill 负责把缩写映射到标准 BMAD skill、SpecKit 指令或 CLI 命令。

### 10.2 维护方式

- 新增缩写：同步编辑 `_bmad/core/tasks/shortcuts-router.md` 与 `~/.codex/skills/bmad-speckit-shortcuts/references/shortcut-map.md` 的映射表。
- 调整速查表：同步更新本文件，保持“文档口径”和“路由口径”一致。
- 升级后：抽查关键映射（`W-PRD`、`W-ARC`、`W-DEV`、`S-PLN`、`S-IMP`、`T-HLP`）是否仍可正确路由。
