# Tasks

- [x] Task 1: 完善工厂 Agent 与可信数据 HUB 接口
  - [x] 新增针对可信数据 HUB 的 skills（如果之前没有）
  - [x] 通过 converse() 对话接口实现 API Key 存储
- [x] Task 2: 实现 Story 1 - 沿街商铺 POI 可信度验证
  - [x] 通过工厂 CLI 与工厂 Agent converse() 对话，确定 2~3 家数据源
  - [x] 通过 converse() 对话获取 API Key，存储到可信数据 HUB
  - [x] 工厂 Agent 生成完整的治理工作包（workpackage）
  - [x] 工作包包含所有脚本、skills 和标准工作入口
- [x] Task 3: 实现 Story 2 - Workpackage 生命周期管理（基础部分）
  - [x] 新增针对 workpackage 的 skills（list、query、dryrun）
  - [x] 实现 workpackage list：列出已发布的工作包
  - [x] 实现 workpackage query：查询工作包详情
  - [x] 实现 workpackage dryrun：试运行测试效果，支持 CLI 调试
  - [x] 实现 workpackage release：在 workpackages/bundles/ 下创建新版本（已支持）
- [x] Task 4: 设计并编写验收用例
  - [x] Story 1 测试用例
  - [x] Story 2 测试用例
  - [x] 端到端测试用例

# Task Dependencies
- Task 1 无依赖，可先执行
- Task 2 依赖 Task 1
- Task 3 可与 Task 2 并行执行
- Task 4 依赖 Task 2-3
