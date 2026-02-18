# 可观测性看板增强 - 直观观察智能体能力与治理效果

## Why
需要在可观测性看板上直观地展示系统的智能体能力（工厂 CLI、工厂 Agent、workpackage 生命周期管理、沿街商铺 POI 可信度验证）以及在数据治理过程中的落地效果和结果观测。让用户能够一目了然地看到：
1. 系统具备哪些智能体能力
2. 这些能力在数据治理过程中的使用情况
3. 治理结果的可信度验证情况

## What Changes
- 新增「智能体能力面板」，直观展示系统当前具备的智能体能力
- 新增「能力使用观测」，展示各能力在数据治理过程中的使用频率和效果
- 新增「沿街商铺 POI 可信度验证结果」面板，直观展示验证结果
- 增强「workpackage 生命周期管理」观测面板，展示 list/query/modify/release/dryrun 的执行情况

## Impact
- 影响系统: 可观测性看板 (`output/dashboard/governance_dashboard.html`)
- 影响代码: `output/dashboard/` 下的相关文件

## ADDED Requirements

### Requirement: 智能体能力面板
系统 SHALL 在可观测性看板上新增「智能体能力面板」，直观展示系统当前具备的智能体能力。

#### 能力列表
1. **工厂 CLI** - 对话式交互
2. **工厂 Agent** - 智能对话、生成治理工作包
3. **可信数据 HUB** - 外部数据源 API Key 管理
4. **Workpackage 生命周期管理** - list/query/modify/release/dryrun
5. **沿街商铺 POI 可信度验证** - 2~3 家外部数据源验证

---

### Requirement: 能力使用观测
系统 SHALL 在可观测性看板上新增「能力使用观测」，展示各能力在数据治理过程中的使用频率和效果。

#### 观测指标
1. 工厂 CLI 对话次数
2. 工厂 Agent 生成的工作包数量
3. 可信数据 HUB 配置的外部数据源数量
4. Workpackage release 次数
5. Workpackage dryrun 次数

---

### Requirement: 沿街商铺 POI 可信度验证结果面板
系统 SHALL 在可观测性看板上新增「沿街商铺 POI 可信度验证结果面板」，直观展示验证结果。

#### 展示内容
1. 验证的沿街商铺 POI 总数
2. 使用的外部数据源（2~3 家）
3. 各数据源的可信度分数分布
4. 验证结果汇总（通过/需人工确认）

---

### Requirement: Workpackage 生命周期管理观测面板
系统 SHALL 增强「workpackage 生命周期管理」观测面板，展示 list/query/modify/release/dryrun 的执行情况。

#### 展示内容
1. 系统中所有 workpackage 列表
2. 各 workpackage 的版本历史
3. Release 次数与时间
4. Dryrun 执行记录与结果
