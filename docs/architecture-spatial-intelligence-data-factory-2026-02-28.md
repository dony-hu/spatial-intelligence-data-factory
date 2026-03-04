# Architecture - 丰图空间智能数据工厂（PRD v1.0 对齐版）

## 1. 文档信息

- 文档版本：v2.0
- 创建日期：2026-02-28
- 上游输入：`docs/prd-spatial-intelligence-data-factory-2026-02-28.md`
- 适用范围：平台核心架构与实施边界（不含行业应用前端）
- 文档语言：中文（遵循仓库 AGENTS 规则）

## 2. 架构目标

围绕 PRD 的核心定位，架构目标如下：

1. 建立统一空间数据工业化生产主链路，支持多源、多模态、可复制交付。
2. 建立“数据 -> 语料 -> 语义 -> 资产”的连续沉淀路径，支撑模型训练与业务复用。
3. 建立 AI 参与生产机制，实现异常检测、辅助标注、规则演化与闭环反馈。
4. 建立可审计、可观测、可治理的工业级运行与质量门禁体系。

## 3. 架构原则

1. 单一主链路：同一类能力只保留一个权威入口，避免脚本化分叉。
2. 契约优先：模块输入/输出必须通过 schema 和版本约束管理。
3. 证据优先：关键处理环节必须产出可追踪证据与审计日志。
4. 分层解耦：控制平面、数据平面、AI 平面职责分离、接口明确。
5. 渐进演进：按 MVP -> 增强 -> 飞轮三阶段推进，避免一次性大改。

## 4. 总体架构（逻辑分层）

### 4.1 控制平面（Control Plane）

职责：任务编排、策略路由、流程治理、门禁裁决。

核心组件：
1. Workflow Orchestrator（任务状态机、重试策略、失败分级）
2. Policy & Rule Manager（规则发布、版本控制、灰度开关）
3. Gate Controller（测试门禁、质量门禁、发布准入）

### 4.2 数据平面（Data Plane）

职责：数据接入、标准化处理、存储沉淀、版本追踪。

核心组件：
1. Ingestion Service（结构化/影像/视频/点云/轨迹接入）
2. Standardization Pipeline（坐标统一、时间对齐、格式转换）
3. Metadata & Lineage Service（元数据登记、血缘追踪、版本快照）
4. Storage Layer（PostgreSQL 多 schema + 对象存储）

### 4.3 模型与语义平面（AI & Semantic Plane）

职责：多模态加工、语料生成、语义知识沉淀、AI 辅助生产。

核心组件：
1. Multimodal Processing Engine（切片、抽帧、向量化、实体识别）
2. Corpus Generation Service（自动标注、伪标签、样本筛选、数据集划分）
3. Spatial Semantic Graph（空间实体模型、行业语义库、关系图）
4. AI Copilot for Production（异常检测、修复建议、规则推荐、样本扩增）

### 4.4 运营与治理平面（Ops & Governance Plane）

职责：可观测、质量控制、资产管理、合规审计。

核心组件：
1. Observability Stack（指标、日志、链路追踪、SLA 监控）
2. Quality Service（完整性校验、统计异常、失败恢复）
3. Data Asset Registry（资产分级、权属标识、生命周期）
4. Audit & Compliance（授权记录、审计追踪、安全检查）

## 5. PRD 功能模块到架构组件映射

1. 数据接入与标准化 -> Ingestion Service + Standardization Pipeline + Metadata & Lineage
2. 多模态加工引擎 -> Multimodal Processing Engine
3. 语料生成系统 -> Corpus Generation Service
4. 空间语义与知识沉淀 -> Spatial Semantic Graph + Semantic API
5. AI 参与生产机制 -> AI Copilot + Rule Manager + Feedback Loop
6. 数据资产管理 -> Data Asset Registry + Audit & Compliance
7. 监控与数据质量 -> Observability Stack + Quality Service + Gate Controller

## 6. 核心链路设计

### 6.1 数据生产主链路

`Data Source -> Ingestion -> Standardization -> Multimodal Processing -> Corpus Generation -> Asset Registry`

关键控制点：
1. 接入时统一校验格式、坐标系、时间戳。
2. 标准化后写入元数据与血缘记录。
3. 加工与语料阶段必须输出质量评分和版本号。

### 6.2 AI 参与生产链路

`Raw/Standardized Data -> AI Detection/Label Assist -> Human Review (Optional) -> Rule Evolution -> Re-run`

关键控制点：
1. AI 输出必须携带置信度与证据片段。
2. 低置信度样本进入人工审核队列。
3. 规则演化需经过回放验证后再发布。

### 6.3 质量门禁与发布链路

`Code/Config/Data Contract Change -> CI Gate -> Quality Gate -> Release Gate -> Production`

关键控制点：
1. 破坏性契约变更自动阻断。
2. KPI 与 SLA 不达标时禁止进入发布阶段。
3. 所有准入决策留痕并可回溯。

## 7. 数据与存储架构

1. 事务数据与运行状态：PostgreSQL（多 schema：governance/runtime/metadata/semantic）。
2. 大对象与多媒体文件：对象存储（按项目/版本分层目录）。
3. 向量与检索索引：向量库或 PG 向量扩展（按场景扩展）。
4. 审计与证据产物：`output/` 统一归档（JSON/JSONL/Markdown）。

## 7.1 WorkPackage Schema 与 Contracts 关系

1. `workpackage_schema` 位于项目一级目录：`/workpackage_schema`，作为工作包协议唯一入口。
2. `workpackage_schema/registry.json` 负责版本索引与当前版本路由，消费者禁止硬编码 schema 文件路径。
3. `contracts/` 继续承载运行时其他契约（API、数据、事件等），`workpackage_schema` 在架构上属于“工作包协议域”的独立模块，通过文档化边界与 `registry` 对接 `contracts` 治理规范。
4. 工作包发布物必须位于 `/workpackages/bundles/<bundle>/`，并通过 `workpackage.json + skills/` 共同构成可执行包。

## 8. 非功能落地设计

### 8.1 性能

1. 支持批处理与流处理混合模式。
2. 多模态加工任务支持并发与分片调度。
3. SLA 超时自动升级告警并触发补偿流程。

### 8.2 可扩展性

1. 插件式算子接口，支持新算法/模型热插拔。
2. 规则、语料、语义模型均采用版本化治理。
3. 按租户/地区隔离配置与策略。

### 8.3 安全与合规

1. RBAC 权限分级与最小权限原则。
2. 数据脱敏与敏感字段访问审计。
3. 全链路操作日志与关键事件不可抵赖存证。

## 9. 分阶段实施蓝图

### Phase 1（0-3 个月，MVP）

1. 打通接入 -> 标准化 -> 语料基础链路。
2. 落地元数据与血缘服务。
3. 建立最小可用质量门禁与可观测看板。

### Phase 2（3-6 个月，增强）

1. 上线 AI 辅助标注与异常检测。
2. 建立语义实体库与关系图基础能力。
3. 完善规则版本发布与回放验证机制。

### Phase 3（6-12 个月，飞轮）

1. 建立业务反馈回流与自动优化闭环。
2. 提升资产复用率与跨项目能力复用。
3. 输出平台化标准能力与商业化交付模板。

## 10. 架构验收标准（DoD）

1. PRD 七大模块均有明确技术承载组件与边界。
2. 三条核心链路（生产、AI、门禁）具备可执行控制点定义。
3. 数据、质量、合规均有对应治理机制与证据输出路径。
4. 可直接作为 `create-story` 与 `dev-story` 的拆解输入。

## 11. 主要风险与缓解

1. 风险：多模态链路复杂，阶段内交付失焦。
- 缓解：按 Now/Next/Later 划定优先级，先确保主链路闭环。

2. 风险：AI 参与机制早期误报率高。
- 缓解：引入置信度阈值 + 人工复核 + 回放评估。

3. 风险：资产化与合规要求提升实施成本。
- 缓解：将审计与权属能力作为平台底座一次建设、持续复用。
