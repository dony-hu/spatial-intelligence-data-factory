# Research: 多地交付数据工厂系统规格

## Decision 1: 采用“双业务基座 + 能力域”作为规划主轴
- Decision: 以“公安地址治理基座、城市运行指挥调度基座”作为一级能力基座。
- Rationale: 与当前在地项目群主线一致，便于跨地区共识与资源组织。
- Alternatives considered: 按地区拆分一级能力；按技术栈拆分一级能力。

## Decision 2: 采用“核心仓治理 + 子仓实现”多仓协同模式
- Decision: 核心仓沉淀标准与共性能力，地区子仓承载落地实现与定制。
- Rationale: 兼顾复用效率与地区差异，避免核心仓被定制需求污染。
- Alternatives considered: 单仓集中式管理；每地完全自治无核心仓。

## Decision 3: 采用“Agent 自动执行 + 人工关键门禁”治理策略
- Decision: 自动化覆盖需求分解、编排、质量扫描、追踪汇总；人工负责口径、合规、发布与 SLA 决策。
- Rationale: 政企场景对可追溯与问责要求高，关键决策必须保留人审。
- Alternatives considered: 全自动闭环；全人工推进。

## Decision 4: 评审门统一化
- Decision: 统一设定业务评审、技术评审、合规评审、发布评审四类门禁。
- Rationale: 让不同地区在同一验收语义下推进，降低跨团队沟通成本。
- Alternatives considered: 各地区自定义门禁；仅保留发布前单一评审。

## Decision 5: 度量聚焦交付而非工具
- Decision: 采用交付周期、复用率、自动化覆盖率、质量达标率、返工率作为统一 KPI。
- Rationale: 直接反映跨团队协同效果与平台化收益。
- Alternatives considered: 仅统计代码量、提交次数等过程指标。
