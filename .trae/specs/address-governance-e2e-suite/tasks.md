# 地址治理全链路 E2E 测试套件 Tasks

## Tasks
- [x] Task 1: 梳理地址治理核心模块流程: 详细分析 ingest, governance, persist, runtime 模块的现有实现，确认关键路径。
  - [x] SubTask 1.1: 梳理 Ingest 模块数据流（API -> Worker）。
  - [x] SubTask 1.2: 梳理 Governance 模块编排逻辑（Pipeline -> Runtime -> Persist）。
  - [x] SubTask 1.3: 梳理 Persist 模块数据模型（Schema）。
- [x] Task 2: 创建测试数据生成器: 开发用于生成测试数据的工具，包括标准地址、脏地址、异常格式数据等。
  - [x] SubTask 2.1: 实现基于 faker 或配置文件的地址生成器。
  - [x] SubTask 2.2: 生成针对 Happy Path 的测试数据集。
  - [x] SubTask 2.3: 生成针对 Manual Review 场景的低置信度数据集。
  - [x] SubTask 2.4: 生成针对 Edge Cases 的异常数据集。
- [x] Task 3: 实现真实基础设施 E2E 测试运行器: 开发支持连接真实 PostgreSQL 和 Worker 的测试框架。
  - [x] SubTask 3.1: 配置测试环境（Docker Compose 或本地服务连接）。
  - [x] SubTask 3.2: 实现测试前的环境准备（数据库清理、Schema 初始化）。
  - [x] SubTask 3.3: 实现测试后的环境清理。
- [x] Task 4: 实现 Happy Path E2E 测试用例: 覆盖标准地址的全流程治理。
  - [x] SubTask 4.1: 编写测试用例：提交标准地址批次。
  - [x] SubTask 4.2: 验证 Worker 处理结果（状态流转、数据持久化）。
  - [x] SubTask 4.3: 验证 API 查询结果（最终产出准确性）。
- [x] Task 5: 实现 Manual Review E2E 测试用例: 覆盖低置信度数据的人工复核流程。
  - [x] SubTask 5.1: 编写测试用例：提交低置信度地址批次。
  - [x] SubTask 5.2: 验证系统生成待复核任务（Review Task）。
  - [x] SubTask 5.3: 模拟人工通过 API 提交复核结果。
  - [x] SubTask 5.4: 验证最终结果更新和审计日志记录。
- [x] Task 6: 实现 Edge Case E2E 测试用例: 覆盖异常输入和并发场景。
  - [x] SubTask 6.1: 编写测试用例：提交 Malformed JSON/CSV。
  - [x] SubTask 6.2: 编写测试用例：并发提交多个大批次任务。
  - [x] SubTask 6.3: 验证系统健壮性（错误处理、重试机制）。

## Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 2], [Task 3]
- [Task 5] depends on [Task 2], [Task 3]
- [Task 6] depends on [Task 2], [Task 3]
