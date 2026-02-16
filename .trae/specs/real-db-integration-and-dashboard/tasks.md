# 真实数据库集成环境与治理看板 Tasks

## Tasks
- [x] Task 1: 搭建本地基础设施环境
  - [x] SubTask 1.1: 创建 `docker-compose.yml` (Postgres + Redis)。
  - [x] SubTask 1.2: 创建 `Makefile` (up, down, logs, test-integration, report)。
  - [x] SubTask 1.3: 验证服务启动与连接。
- [x] Task 2: 修复 Governance API Postgres 集成测试 (P0)
  - [x] SubTask 2.1: 在本地 DB 环境下运行 `test_rulesets_postgres_integration.py`。
  - [x] SubTask 2.2: 调试并修复失败原因。
  - [x] SubTask 2.3: 验证测试稳定通过。
- [x] Task 3: 增强 E2E 测试报告与数据采集
  - [x] SubTask 3.1: 修改 `test_address_governance_full_cycle.py`，支持输出 JSON 报告到 `output/lab_mode/governance_e2e_latest.json`。
  - [x] SubTask 3.2: 创建 `scripts/collect_governance_metrics.py`，连接 DB 统计治理指标并生成 `output/dashboard/governance_metrics.json`。
  - [x] SubTask 3.3: 集成到 `Makefile` 的 `report` 目标中。
- [x] Task 4: 实现治理看板前端
  - [x] SubTask 4.1: 创建 `output/dashboard/governance_dashboard.html`。
  - [x] SubTask 4.2: 实现前端逻辑：读取 `governance_metrics.json` 并渲染图表/数据卡片。
  - [x] SubTask 4.3: 实现前端逻辑：读取 `governance_e2e_latest.json` 展示测试结果。
  - [x] SubTask 4.4: 添加 "数据前后对比" 表格组件。

## Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 3]
