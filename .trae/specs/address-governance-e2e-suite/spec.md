# 地址治理全链路 E2E 测试套件 Spec

## Why
当前系统的 E2E 测试主要依赖内存模式，缺乏在真实基础设施（PostgreSQL, Worker）环境下的全链路验证。同时，人工复核（Manual Review）和业务逻辑准确性的端到端测试覆盖不足，无法充分保障地址治理核心流程的稳定性。

## What Changes
- 创建一个新的 E2E 测试套件，专门针对地址治理场景。
- 实现真实基础设施（Real Infrastructure）模式的测试运行器。
- 覆盖以下核心流程：
  - **Happy Path**: 正常地址的摄入、治理、持久化及结果验证。
  - **Manual Review Loop**: 低置信度地址的人工复核闭环。
  - **Edge Cases**: 异常输入处理和并发场景。

## Impact
- **Affected specs**: `system-status-planning` (可能会更新测试状态)
- **Affected code**: `tests/` 目录，可能会增加新的测试文件和辅助工具。

## ADDED Requirements

### Requirement: 真实环境集成测试
系统 SHALL 提供一种机制，能够在连接真实 PostgreSQL 和 Worker 的环境下运行 E2E 测试，而不是仅依赖内存模拟。

#### Scenario: 真实环境下的全流程
- **WHEN** 运行 E2E 测试套件
- **THEN** 测试应当连接到真实的数据库和消息队列（或模拟的真实行为），验证数据在各服务间的正确流转。

### Requirement: 业务逻辑准确性验证
系统 SHALL 验证特定输入地址在经过治理流程后，其输出的 `canonical_address` 是否符合预期。

#### Scenario: 地址清洗验证
- **WHEN** 输入脏地址 "上海市浦东新区世纪大道100号"
- **THEN** 系统应当输出标准化的结构化地址，并持久化到数据库。

### Requirement: 人工复核闭环验证
系统 SHALL 验证低置信度数据触发人工复核流程，并在人工干预后更新最终结果。

#### Scenario: 低置信度复核
- **WHEN** 输入低置信度地址
- **THEN** 系统生成待复核任务
- **WHEN** 人工提交修正结果
- **THEN** 系统更新最终状态为已完成，并记录审计日志。
