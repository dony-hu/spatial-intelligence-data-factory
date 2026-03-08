# Story: MVP-A1 CLI-Agent-LLM 对话确认治理需求

## 目标

通过工厂 CLI 与工厂 Agent 完成一次对话式地址治理需求确认，并由 Agent 调用 LLM 输出结构化治理方案摘要。

## 验收标准

1. CLI 可提交治理需求提示词并接收 Agent 响应。
2. Agent 必须调用真实 LLM 生成结构化方案摘要，不允许 fallback。
3. 响应至少包含：目标、数据源、规则要点、输出物清单。
4. LLM 不可用或响应不合约时必须 fail-fast，产出阻塞报告并等待人工确认方案。

## 开发任务

1. 先补测试：CLI->Session->Agent 链路失败/成功用例。
2. 再改实现：完善对话路由与结构化响应字段。
3. 最后验证：执行最小对话脚本并输出证据。

## 测试用例

1. 输入“请生成地址治理 MVP 方案”返回结构化摘要。
2. 模拟 LLM 不可用时流程中止并记录 `blocked` 状态，禁止返回降级结果。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC A（结果可信）+ EPIC B（编排可控）+ No-Fallback 要求。
2. 架构对齐：
- `docs/02_总体架构/系统总览.md`
- `docs/02_总体架构/模块边界.md`
- `docs/02_总体架构/依赖关系.md`

## 模块边界与 API 边界

1. 所属模块：`factory_cli`、`factory_agent`、`llm_gateway`、`audit`。
2. 上游入口：CLI 对话命令。
3. 下游依赖：Agent 意图路由、LLM Gateway、审计写入。
4. API 边界：仅允许 CLI -> Agent -> LLM Gateway，禁止 CLI 直连数据库。

## 依赖与禁止耦合

1. 允许依赖：`factory_cli -> factory_agent -> llm_gateway`。
2. 禁止耦合：
- `factory_cli -> PostgreSQL` 直连。
- 在 Agent 中直接绑定具体 LLM SDK 客户端对象并跨模块透传。
