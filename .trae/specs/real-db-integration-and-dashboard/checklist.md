# 真实数据库集成环境与治理看板 Checklist

- [x] Task 1: 搭建本地基础设施环境
  - [x] 1.1 docker-compose.yml 可正常启动 Postgres/Redis
  - [x] 1.2 Makefile 命令可用 (make up/down/test)
  - [x] 1.3 数据库连接验证通过
- [x] Task 2: 修复 Governance API Postgres 集成测试 (P0)
  - [x] 2.1 test_rulesets_postgres_integration.py 在真实 DB 下运行通过
  - [x] 2.2 无逻辑错误或异常抛出
- [x] Task 3: 增强 E2E 测试报告与数据采集
  - [x] 3.1 E2E 测试能生成标准 JSON 报告
  - [x] 3.2 collect_governance_metrics.py 能准确统计 DB 数据
  - [x] 3.3 governance_metrics.json 文件格式符合预期
- [x] Task 4: 实现治理看板前端
  - [x] 4.1 governance_dashboard.html 页面可访问
  - [x] 4.2 能够展示 E2E 测试结果 (Pass/Fail)
  - [x] 4.3 能够展示 DB 中的治理数据统计 (Raw vs Canonical)
  - [x] 4.4 能够展示数据样例对比
