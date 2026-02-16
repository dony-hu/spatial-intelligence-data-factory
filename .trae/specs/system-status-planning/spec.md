# 系统现状梳理与任务规划 Spec

## Why

基于之前的测试结果和系统分析，需要梳理当前各工作线的状态，并规划后续任务，确保 Iteration-005 和 Iteration-006 的目标能够顺利完成。

## What Changes

- 梳理当前各工作线的测试状态
- 规划待处理任务的优先级和顺序
- 明确各项任务的验收标准

## Impact

- Affected specs: 所有工作线
- Affected code: 多个服务和包

## 当前系统现状

### 已验证通过的工作线
1. **产线执行线 (Line Execution)**: ✅ 5/5 测试通过
2. **P0 工作包测试**: ✅ 6/6 测试通过
3. **地址核心算法线 (Address Core)**: ✅ 19/19 测试通过
4. **治理 Worker 线 (Governance Worker)**: ✅ 4/4 测试通过
5. **可信数据 Hub 线 (Trust Data Hub)**: ✅ 12/12 测试通过（已修复）

### 基本通过的工作线
1. **治理 API 线 (Governance API)**: ⚠️ 34/35 测试通过
   - 失败项：`test_activate_ruleset_requires_approved_change_request_postgres`

### 待处理任务
1. 设计 line_feedback schema v2 (Production Line workline)
2. 统一进度口径 (Orchestrator workline)
3. 统一超时策略 (Core Engine workline)

### Iteration-005 目标
- 完成工程监理线可视化 + 项目介绍双层结构 + 四卡片 + sticky 摘要 + 密度切换
- 完成派单字段规范化（A/R/Agent/Skill）并纳入研发门禁
- 修复夜间 web_e2e 门槛失败并恢复统一 GO 口径
- 完成项目管理总控线接任与恢复闭环

## ADDED Requirements

### Requirement: 系统现状梳理
系统 SHALL 提供清晰的各工作线状态报告，包括：
- 测试通过情况
- 待修复问题
- 待处理任务优先级

#### Scenario: 查看各工作线状态
- **WHEN** 用户查看系统状态
- **THEN** 用户能看到各工作线的测试通过情况和待处理任务

### Requirement: 任务优先级规划
系统 SHALL 按优先级规划待处理任务：
1. P0: 修复 Governance API 测试失败
2. P1: 设计 line_feedback schema v2
3. P2: 统一进度口径
4. P3: 统一超时策略

#### Scenario: 任务按优先级执行
- **WHEN** 执行任务规划
- **THEN** 任务按优先级顺序执行，高优先级任务先完成
