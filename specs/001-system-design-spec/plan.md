# Implementation Plan: 多地交付数据工厂系统规格

**Branch**: `001-system-design-spec` | **Date**: 2026-02-11 | **Spec**: [/Users/01411043/code/spatial-intelligence-data-factory/specs/001-system-design-spec/spec.md](/Users/01411043/code/spatial-intelligence-data-factory/specs/001-system-design-spec/spec.md)
**Input**: Feature specification from `/specs/001-system-design-spec/spec.md`

## Summary

围绕“公安地址治理基座 + 城市运行指挥调度基座”建立系统级规格与协同治理机制，定义核心仓与五个子仓的职责边界、阶段产物、评审门禁和度量标准，形成可并行推进、可审计回溯的人机协同交付体系。

## Technical Context

**Language/Version**: Markdown 规范文档 + Shell 自动化脚本（仓库现状）  
**Primary Dependencies**: GitHub 仓库协作、Spec Kit 工作流、BMAD 方法文档资产  
**Storage**: Git 仓库文件系统（核心仓 + 子仓）  
**Testing**: 文档评审检查清单 + 交付物完整性检查  
**Target Platform**: GitHub 托管的多仓协作环境与本地 Codex 执行环境  
**Project Type**: 文档驱动的治理与架构设计项目（非单体应用开发）  
**Performance Goals**: 5 个子仓在同一迭代窗口内完成规格对齐并进入执行阶段  
**Constraints**: 合规强约束、人审门禁必须保留、核心仓与子仓必须隔离管理  
**Scale/Scope**: 1 个核心仓 + 5 个地区子仓 + 跨地域多角色团队

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

当前 `.specify/memory/constitution.md` 仍为模板占位内容，暂无法执行正式宪章规则校验。为保证推进，本轮采用项目既有治理规则作为临时门禁：

- 门禁 1：文档与治理产物默认中文输出（通过）
- 门禁 2：核心仓与子仓职责隔离，定制需求不得回灌核心仓（通过）
- 门禁 3：关键决策必须定义人工审批责任角色（通过）
- 门禁 4：阶段交付物可追溯且可审计（通过）

结论：在临时门禁下可进入 Phase 0/1；建议后续补齐正式 constitution。

## Project Structure

### Documentation (this feature)

```text
specs/001-system-design-spec/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── governance-workflow.openapi.yaml
├── checklists/
│   └── requirements.md
└── spec.md
```

### Source Code (repository root)

```text
/Users/01411043/code/spatial-intelligence-data-factory/
├── README.md
├── AGENTS.md
├── bmad/
├── docs/
│   ├── kickoff/
│   ├── architecture-alignment-spatial-intelligence-data-factory-2026-02-11.md
│   └── ...
├── logs/
├── schemas/
├── scripts/
├── templates/
└── specs/
    └── 001-system-design-spec/

# 协同外部子仓（同级目录，逻辑纳入本规划）
/Users/01411043/code/project-shanghai-address-governance
/Users/01411043/code/project-kunshan-panorama-3dgs-labeling
/Users/01411043/code/project-wujiang-public-security-governance
/Users/01411043/code/project-beijing-public-security-governance
/Users/01411043/code/project-baoan-city-command
```

**Structure Decision**: 采用“核心仓治理 + 子仓业务实现”的多仓结构。核心仓承载方法、标准与共性资产；子仓承载地区场景实现与定制交付。

## Phase 0 Research Plan

- 研究项 A：双业务基座能力域边界与复用判定规则
- 研究项 B：跨仓里程碑协同与评审门禁设计
- 研究项 C：Agent 自动化与人工审批的最小闭环
- 研究项 D：多地交付下的审计追踪与度量机制

## Phase 1 Design Plan

- 产出 `data-model.md`：定义基座、能力域、评审门、交付包、人机协同任务等核心实体
- 产出 `contracts/governance-workflow.openapi.yaml`：定义治理流程与评审记录接口契约
- 产出 `quickstart.md`：定义首轮落地步骤（核心仓发布、子仓对齐、例会节奏、验收口径）
- 更新 Agent 上下文：执行 `.specify/scripts/bash/update-agent-context.sh codex`

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 宪章未正式定义 | 先启动系统规格设计，避免等待阻塞 | 等宪章完成后再启动会延误跨团队对齐窗口 |
