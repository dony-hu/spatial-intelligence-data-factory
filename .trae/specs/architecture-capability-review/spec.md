# 架构、规格与现状能力梳理 Spec

## Why
需要对当前所有 specs 进行系统性梳理，明确系统架构、规格定义和现状能力，识别冲突和待完善项，为后续开发提供清晰的路线图。

## What Changes
- 梳理 8 个 change-id 的规格定义
- 分析系统架构层次和能力边界
- 识别各 spec 之间的关系和潜在冲突
- 输出现状能力全景图和待完善建议

## Impact
- **Affected specs**: 所有 8 个现有 specs
- **Affected code**: 无代码改动，仅文档梳理

---

## 核心架构原则

### 1. 地址治理仅作为架构验证实例
- **定位**: 地址治理是用来跑通架构的一个实例，**不是核心业务能力**
- **代码位置**: 地址相关内容本质应该在**测试用例**里，不应该出现在核心代码仓库里
- **当前阶段**: 开发阶段允许一部分侵入，便于打通流程；后续应逐步剥离到测试或独立 WorkPackage

### 2. 工厂 Agent 与治理 Runtime 分离
- **工厂 Agent (🧠 大脑)**: 负责理解意图、生成 WorkPackage、管理生命周期
- **治理 Runtime (⚙️ 业务执行框架)**: 负责调度和执行 WorkPackage
- **治理执行体 (📦 WorkPackage 内容)**: 具体业务逻辑，由工厂 Agent 生成，由治理 Runtime 执行

---

## 系统架构全景

### 顶层架构关系
```mermaid
graph TB
    subgraph "顶层架构"
        A[工厂 Agent&lt;br/&gt;🧠 大脑]
        B[治理 Runtime&lt;br/&gt;⚙️ 业务执行框架]
        C[治理执行体&lt;br/&gt;📦 WorkPackage 内容]
    end

    A --&gt;|生成| C
    B --&gt;|调度执行| C
```

**说明**:
- **工厂 Agent (🧠 大脑)**: 负责理解用户意图、生成治理工作包 (WorkPackage)、管理 WorkPackage 生命周期
- **治理 Runtime (⚙️ 业务执行框架)**: 负责调度和执行工厂 Agent 生成的 WorkPackage
- **治理执行体 (📦 WorkPackage 内容)**: 具体的治理脚本、技能和标准入口，由工厂 Agent 生成，由治理 Runtime 执行

---

### 五层架构（在顶层架构框架下）
```mermaid
graph TB
    subgraph "顶层架构"
        TopA[工厂 Agent&lt;br/&gt;🧠 大脑]
        TopB[治理 Runtime&lt;br/&gt;⚙️ 业务执行框架]
        TopC[治理执行体&lt;br/&gt;📦 WorkPackage 内容]
    end

    subgraph "交互层 (Interaction Layer)"
        A[工厂 CLI]
        B[工厂 Agent]
    end

    subgraph "核心层 (Core Layer)"
        C[Workpackage 生命周期管理]
        D[可信数据 HUB]
    end

    subgraph "业务层 (Business Layer)"
        E[地址治理]
        F[沿街商铺 POI 可信度验证]
    end

    subgraph "基础设施层 (Infrastructure Layer)"
        G[PostgreSQL]
        H[Redis]
        I[治理 Worker]
    end

    subgraph "可观测层 (Observability Layer)"
        J[治理看板]
        K[E2E 测试套件]
    end

    TopA -.映射到.-&gt; B
    TopB -.映射到.-&gt; I
    TopC -.映射到.-&gt; E &amp; F

    A &lt;--&gt; B
    B --&gt; C
    B --&gt; D
    C --&gt; E
    D --&gt; F
    E &amp; F --&gt; G &amp; H &amp; I
    G &amp; I --&gt; J
    G &amp; I --&gt; K
```

---

## 各 Spec 能力与完成度

| Change-ID | 核心能力 | 状态 | 完成度 | 关联 Specs |
|-----------|---------|------|--------|-----------|
| **workpackage-structure-design** | WorkPackage 目录结构定义 | ✅ 设计完成 | 100% | poi-shop-trust-verification |
| **trust-data-hub-phase1** | API Key 管理、外部数据源集成 | ✅ 完成 | 100% | poi-shop-trust-verification |
| **real-db-integration-and-dashboard** | 真实 DB 基础设施、治理看板 | ✅ 完成 | 100% | address-governance-e2e-suite, system-status-planning |
| **address-governance-e2e-suite** | 地址治理全链路 E2E 测试 | ✅ 完成 | 100% | real-db-integration-and-dashboard |
| **observability-and-docs-improvement** | 看板自动化、文档规范化 | ⚠️ 部分完成 | 75% | real-db-integration-and-dashboard |
| **system-status-planning** | 系统现状梳理、任务规划 | ✅ 完成 | 100% | 所有 |
| **poi-shop-trust-verification** | POI 可信度验证、Workpackage 生命周期 | ⚠️ 部分完成 | 80% | trust-data-hub-phase1, workpackage-structure-design |
| **observability-dashboard-enhancement** | 智能体能力面板、能力使用观测 | ⏳ 未开始 | 0% | poi-shop-trust-verification |

---

## Spec 冲突分析

### 潜在冲突点
1. **Workpackage 生命周期管理的 scope 定义**
   - `poi-shop-trust-verification` 定义了 list/query/modify/release/dryrun
   - `workpackage-structure-design` 仅定义了目录结构
   - **结论**: 无冲突，互补

2. **可观测性看板的内容范围**
   - `real-db-integration-and-dashboard` 定义了基础治理指标
   - `observability-dashboard-enhancement` 定义了智能体能力增强
   - **结论**: 无冲突，是递进关系

3. **E2E 测试的责任边界**
   - `address-governance-e2e-suite` 负责地址治理业务
   - `real-db-integration-and-dashboard` 负责基础设施集成
   - **结论**: 无冲突，分层清晰

---

## 现状能力总结

### ✅ 已完全交付的能力
1. **基础设施层**: Docker Compose (Postgres + Redis) + Makefile
2. **数据治理核心**: 地址治理全链路 (Ingest → Governance → Persist)
3. **可信数据 HUB**: API Key 安全存储与管理
4. **WorkPackage 结构**: 目录结构与标准入口定义
5. **基础可观测性**: 治理看板 (指标 + E2E 结果)
6. **测试体系**: E2E 测试套件 + Postgres 集成测试

### ⚠️ 部分交付的能力
1. **WorkPackage 生命周期**: list/query/dryrun 完成，modify/release 待完善
2. **POI 可信度验证**: 框架完成，端到端验收待验证
3. **可观测性增强**: 看板自动化完成，智能体能力面板待实现

### ⏳ 待启动的能力
1. **智能体能力面板**: 5 项能力展示
2. **能力使用观测**: 5 项指标统计
3. **POI 验证结果面板**: 验证结果可视化

---

## 后续优先级建议

### P0 - 高优先级（1-2 周）
1. 完成 `poi-shop-trust-verification` 的 Story 2 剩余部分 (modify/release)
2. 完成 `observability-dashboard-enhancement` 的 4 个任务

### P1 - 中优先级（2-4 周）
1. 完成 `observability-and-docs-improvement` 的 Task 4 (统一配置管理)
2. 设计并实现 `observability-dashboard-enhancement` 与 `poi-shop-trust-verification` 的数据联动

### P2 - 低优先级（1-2 月）
1. 优化 E2E 测试覆盖率
2. 完善文档体系

---

## ADDED Requirements
无新增需求，仅现状梳理。

## MODIFIED Requirements
无修改需求。

## REMOVED Requirements
无删除需求。
