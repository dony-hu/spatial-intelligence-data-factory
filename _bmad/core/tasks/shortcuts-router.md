---
name: shortcuts-router
description: 'Resolve shorthand BMAD and SpecKit aliases into standard commands/workflows/agents/tasks and route execution.'
---

# Task: BMAD + SpecKit Shortcuts Router

Use this task when the user enters shorthand aliases such as `W-ARC`, `S-PLN`, `A-PM + W-PRD`, or `C-STS`.

## Alias Prefixes

- `C-` = CLI command
- `W-` = workflow
- `S-` = SpecKit command
- `A-` = agent
- `T-` = core task

## Parse Rules

- Accept Chinese and English phrases (for example: `执行 W-ARC`, `Run W-ARC`).
- Treat `+`, `then`, `再`, and `,` as sequential separators.
- If multiple aliases are present, execute in order.

## Mapping Table

### CLI (`C-`)

- `C-INS` / `C-install` / `C-安装` -> `bmad install`
- `C-STS` / `C-status` / `C-状态` -> `bmad status`
- `C-UNS` / `C-uninstall` / `C-卸载` -> `bmad uninstall`
- `C-HLP` / `C-help` / `C-帮助` -> `bmad help`

### Workflows (`W-`)

- `W-BRF` / `W-brief` / `W-产品简报` -> `bmad-bmm-create-product-brief`
- `W-PRD` / `W-需求文档` -> `bmad-bmm-create-prd`
- `W-VPRD` / `W-验证需求` -> `bmad-bmm-validate-prd`
- `W-EPRD` / `W-修订需求` -> `bmad-bmm-edit-prd`
- `W-UXD` / `W-体验设计` -> `bmad-bmm-create-ux-design`
- `W-ARC` / `W-architecture` / `W-架构设计` -> `bmad-bmm-create-architecture`
- `W-EPS` / `W-史诗拆分` -> `bmad-bmm-create-epics-and-stories`
- `W-SPLN` / `W-冲刺规划` -> `bmad-bmm-sprint-planning`
- `W-STR` / `W-story` / `W-创建故事` -> `bmad-bmm-create-story`
- `W-DEV` / `W-故事开发` -> `bmad-bmm-dev-story`
- `W-CR` / `W-代码评审` -> `bmad-bmm-code-review`
- `W-RDY` / `W-实施就绪` -> `bmad-bmm-check-implementation-readiness`
- `W-RET` / `W-冲刺复盘` -> `bmad-bmm-retrospective`
- `W-CC` / `W-方案纠偏` -> `bmad-bmm-correct-course`
- `W-SSTS` / `W-冲刺进展` -> `bmad-bmm-sprint-status`
- `W-QSP` / `W-快速方案` -> `bmad-bmm-quick-spec`
- `W-QDV` / `W-快速开发` -> `bmad-bmm-quick-dev`
- `W-DRS` / `W-领域研究` -> `bmad-bmm-domain-research`
- `W-MRS` / `W-市场研究` -> `bmad-bmm-market-research`
- `W-TRS` / `W-技术研究` -> `bmad-bmm-technical-research`
- `W-GCTX` / `W-项目上下文` -> `bmad-bmm-generate-project-context`
- `W-DOC` / `W-项目文档` -> `bmad-bmm-document-project`
- `W-E2E` / `W-端到端测` -> `bmad-bmm-qa-generate-e2e-tests`
- `W-STP` / `W-story-pipeline` / `W-故事流水线` -> `bmad-story-pipeline`
- `W-STW` / `W-story-worktree` / `W-story-pipeline-worktree` / `W-故事工作树` -> `bmad-story-pipeline-worktree`
- `W-EPW` / `W-epic-worktree` / `W-epic-pipeline-worktree` / `W-史诗工作树` -> `bmad-epic-pipeline-worktree`

### SpecKit (`S-`)

- `S-SPC` / `S-specify` / `S-规格定义` -> `/speckit.specify`
- `S-CLF` / `S-clarify` / `S-规格澄清` -> `/speckit.clarify`
- `S-PLN` / `S-plan` / `S-实现规划` -> `/speckit.plan`
- `S-TSK` / `S-tasks` / `S-任务拆解` -> `/speckit.tasks`
- `S-IMP` / `S-implement` / `S-任务实施` -> `/speckit.implement`
- `S-ANL` / `S-analyze` / `S-一致性分析` -> `/speckit.analyze`
- `S-CHK` / `S-checklist` / `S-验收清单` -> `/speckit.checklist`
- `S-T2I` / `S-taskstoissues` / `S-任务建单` -> `/speckit.taskstoissues`
- `S-CST` / `S-constitution` / `S-宪章更新` -> `/speckit.constitution`

### Agents (`A-`)

- `A-BMAD` / `A-总控` -> `bmad-agent-bmad-master`
- `A-ANL` / `A-分析师` -> `bmad-agent-bmm-analyst`
- `A-PM` / `A-产品经理` -> `bmad-agent-bmm-pm`
- `A-ARC` / `A-架构师` -> `bmad-agent-bmm-architect`
- `A-UX` / `A-体验设计` -> `bmad-agent-bmm-ux-designer`
- `A-DEV` / `A-开发工程` -> `bmad-agent-bmm-dev`
- `A-QA` / `A-测试工程` -> `bmad-agent-bmm-qa`
- `A-SM` / `A-敏捷教练` -> `bmad-agent-bmm-sm`
- `A-TW` / `A-技术写作` -> `bmad-agent-bmm-tech-writer`
- `A-SOLO` / `A-单人快开` -> `bmad-agent-bmm-quick-flow-solo-dev`

### Core tasks (`T-`)

- `T-HLP` / `T-流程导航` -> `bmad-help`
- `T-IDX` / `T-文档索引` -> `bmad-index-docs`
- `T-SHD` / `T-文档分片` -> `bmad-shard-doc`

## Execution Rules

1. Echo the parsed route before execution: `input -> target`.
2. For `C-`: run the CLI command and summarize result.
3. For `W-`/`A-`/`T-`: route to the mapped BMAD command/agent/task exactly.
4. For `S-`: route to the mapped SpecKit command exactly.
5. If a step fails in a sequence, stop and ask whether to continue.

## Safety Rules

- If alias is unknown, suggest `bmad-shortcuts-router` help and ask for one clear alias.
- Never invent commands, workflows, roles, or files.
