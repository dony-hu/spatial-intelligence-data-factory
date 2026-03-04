# 可观测交互页面 Spec

## Why
需要一个可视化页面来展示 story 执行过程中的完整交互链路，包括：
1. 测试系统 ↔ 工厂 Agent 的 converse() 交互
2. 工厂 Agent ↔ 治理 Runtime 的调用
3. 治理 Runtime 执行 WorkPackage 的过程
4. 相关的观测数据（runtime_observability、gate_alignment 等）

## What Changes
- 整合现有 observability 体系（line_observe.py、runtime metrics、gate_alignment）
- 扩展交互记录，包含完整链路的三层交互
- 支持查看 Runtime 执行过程和观测数据
- 支持查看 WorkPackage 版本和 observability bundle

## Impact
- **Affected specs**: poi-shop-trust-verification, observability-and-docs-improvement
- **Affected code**: scripts/、output/dashboard/、workpackages/bundles/*/observability/

---

## 现有 Observability 体系整合

### 1. WorkPackage Observability Bundle
每个 workpackage bundle 包含：
- `observability/line_observe.py` - 产线观测脚本
- `observability/line_metrics.json` - 产线指标

### 2. Runtime Observability 数据
由 `line_execution_tc06.py` 收集：
- `step_total`, `step_failed`, `step_error_rate`
- `by_step` - 按步骤分解
- 嵌入到 `line_feedback` 合约中

### 3. Observability Snapshot
由 `services/governance_api/app/routers/lab.py` 生成：
- `l3.gate_alignment` - 门槛对齐状态
- `release_decision`, `failed_gates`, `no_go_risk`
- `metric_explanations` - 指标解释

---

## ADDED Requirements

### Requirement: 三层交互链路可观测
系统 SHALL 提供完整的三层交互链路可观测：

#### 层次 1：测试系统 ↔ 工厂 Agent
- 记录每次 converse() 调用
- 包含：时间戳、输入 prompt、输出响应

#### 层次 2：工厂 Agent ↔ 治理 Runtime
- 记录 workpackage 生成/发布/查询等操作
- 包含：workpackage_id、version、action 类型

#### 层次 3：治理 Runtime ↔ 执行 WorkPackage
- 记录 workpackage 执行过程
- 包含：runtime_observability（step_error_rate 等）
- 包含：observability bundle（line_observe.py、line_metrics.json）

---

### Requirement: 可观测交互页面
系统 SHALL 提供一个可观测交互页面，展示完整的交互链路。

#### Scenario: 三层交互记录展示
- **WHEN** 用户执行端到端测试
- **THEN** 三层交互都被记录
- **AND** 可观测页面按时间线展示完整链路

#### Scenario: Runtime 执行数据查看
- **WHEN** 用户查看某条 Runtime 交互
- **THEN** 显示 runtime_observability 数据
- **AND** 显示 observability bundle 内容
- **AND** 显示 gate_alignment 状态

#### Scenario: 交互详情查看
- **WHEN** 用户点击某条交互记录
- **THEN** 展开显示该次交互的完整详情
- **AND** 支持收起详情

#### Scenario: 交互记录导出
- **WHEN** 用户点击导出按钮
- **THEN** 下载完整交互记录的 JSON 文件

---

## MODIFIED Requirements
无

## REMOVED Requirements
无
