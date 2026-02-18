# 空间智能数据工厂 - 智能体增强（Story 合集）

## Story 1: 沿街商铺 POI 可信度验证

### Why
对于沿街商铺 POI 的地址治理，需要通过至少两家可信外部数据源进行可信度验证，以确保地址的准确性和可信度。同时，这是一个**关键验收场景**，用于验证工厂 CLI、工厂 Agent 和数据治理产线的协同，以及打通工厂 CLI 到可信数据 HUB 的链路。

### What Changes
- 新增「沿街商铺 POI 可信度验证」功能
- 通过工厂 CLI 和工厂 Agent 对话交互确定 2~3 家外部可信数据源
- 通过工厂 CLI 和工厂 Agent 对话提供 API Key，存储到可信数据 HUB
- 工厂 Agent 生成完整的治理工作包（workpackage），包含所有脚本和 skills，以及标准工作入口
- **约束**: 整个开发过程不允许直接修改 workpackage 中的内容，所有内容必须通过工厂 Agent 生成
- **观测项**: workpackage 中的内容是通过工厂 Agent 生成的

### Impact
- 影响系统: 工厂 CLI、工厂 Agent、可信数据 HUB、数据治理产线
- 影响代码: `packages/factory_agent/`, `packages/factory_cli/`, `packages/trust_hub/`, `workpackages/`
- **验收目标**: 验证工厂 CLI ↔ 工厂 Agent ↔ 数据治理产线的协同，以及工厂 CLI 到可信数据 HUB 的打通

### ADDED Requirements

#### Requirement: 沿街商铺 POI 可信度验证
系统 SHALL 提供沿街商铺 POI 地址的可信度验证功能，通过至少两家可信外部数据源 API 进行打分。

##### Scenario: 成功验证沿街商铺 POI（关键验收场景）
- **WHEN** 用户通过工厂 CLI 用自然语言发起「沿街商铺 POI 可信度验证」请求
- **AND** 用户通过工厂 CLI 与工厂 Agent（对接 LLM）智能对话，确定 2~3 家外部可信数据源（不限于图商）
- **AND** 用户通过工厂 CLI 与工厂 Agent 对话提供这些数据源的 API Key
- **AND** 工厂 Agent 生成完整的治理工作包（workpackage），包含所有脚本和 skills，以及标准工作入口
- **AND** 工厂 Agent 将 API Key 存储到可信数据 HUB
- **THEN** 治理产线执行该工作包，对沿街商铺 POI 进行 2~3 家数据源的可信度打分
- **AND** 输出验证结果
- **AND** **观测项**: workpackage 中所有内容均通过工厂 Agent 生成，无直接人工修改

---

## Story 2: Workpackage 生命周期管理

### Why
需要支持 workpackage 的完整生命周期管理，通过工厂 CLI 查询、修改、发布系统中所有工作包的信息。工厂 Agent 应该有一组针对 workpackage 的技能可以被使用：list、query、modify、release。每次 release，应该带来 workpackage 目录下面的一次版本发布。另外，工作包可以被 dryrun，在没有发布成 workpackage 时，通过工厂 Agent 试运行测试效果，通过工厂 CLI 进行数据处理流程的调试。

### What Changes
- 工厂 Agent 新增一组针对 workpackage 的技能：list、query、modify、release、dryrun
- 支持 workpackage 的版本发布（每次 release 在 workpackages/bundles/ 下创建新版本目录）
- 支持 dryrun 模式：在发布前试运行测试效果，通过工厂 CLI 进行调试

### Impact
- 影响系统: 工厂 CLI、工厂 Agent、workpackages/
- 影响代码: `packages/factory_agent/`, `packages/factory_cli/`, `workpackages/bundles/`

### ADDED Requirements

#### Requirement: Workpackage 生命周期管理
系统 SHALL 提供 workpackage 的完整生命周期管理能力：list、query、modify、release、dryrun。

##### Scenario: Workpackage 版本发布
- **WHEN** 用户通过工厂 CLI 与工厂 Agent 对话，执行 workpackage release
- **THEN** 工厂 Agent 在 `workpackages/bundles/` 下创建新版本目录
- **AND** 新版本包含完整的治理脚本、skills 和标准工作入口

##### Scenario: Workpackage Dryrun
- **WHEN** 用户通过工厂 CLI 与工厂 Agent 对话，执行 workpackage dryrun
- **THEN** 工厂 Agent 试运行测试效果
- **AND** 用户通过工厂 CLI 进行数据处理流程的调试

---

## MODIFIED Requirements

无

## REMOVED Requirements

无
