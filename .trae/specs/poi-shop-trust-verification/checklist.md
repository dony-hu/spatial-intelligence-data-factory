# Checklist

## Story 1: 沿街商铺 POI 可信度验证
- [x] 工厂 CLI 与工厂 Agent 仅通过 converse() 对话交互，无新增 API
- [x] 工厂 Agent 通过 converse() 对话确定 2~3 家外部可信数据源
- [x] 工厂 Agent 通过 converse() 对话获取 API Key，存储到可信数据 HUB
- [x] 工厂 Agent 生成完整的治理工作包（workpackage）
- [x] 工作包包含所有脚本、skills 和标准工作入口
- [x] workpackage 中所有内容均通过工厂 Agent 生成，无直接人工修改

## Story 2: Workpackage 生命周期管理
- [x] 工厂 Agent 新增针对 workpackage 的 skills（list、query、dryrun）
- [x] workpackage release 在 workpackages/bundles/ 下创建新版本目录（已支持）
- [x] workpackage query 支持查询工作包详情
- [x] workpackage dryrun 支持试运行测试效果，通过 CLI 调试
- [x] 观测项：workpackage 内容由 Agent 生成，无直接人工修改
