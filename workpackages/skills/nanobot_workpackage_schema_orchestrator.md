---
name: nanobot_workpackage_schema_orchestrator
version: v1.0.0
owner: factory-agent
scope: address-governance
---

# nanobot 工作包协议编排技能

## 目标
- 用户只提供业务目标与确认决策。
- nanobot 主动按 `workpackage_schema.v1` 收敛缺口并推动生成可执行工作包。

## 执行准则
1. 不要求用户记忆或输入 schema 字段名。
2. 仅向用户询问必须由人工提供的信息：
- 业务目标优先级
- 验收阈值/风险偏好
- 外部 API key 与授权
3. 其余结构化内容由 nanobot 内部组织并传递给 opencode。
4. 失败时显式阻断并反馈真实错误；禁止 mock/fallback/workground。

## 必须覆盖的 schema 块
1. `workpackage`
2. `architecture_context`
3. `io_contract`
4. `api_plan`
5. `execution_plan`
6. `scripts`

## 对用户的话术模板
- 首轮确认：
  - “我将按内部工作包协议自动收敛方案。你只需确认治理目标与关键约束。”
- 依赖确认：
  - “以下外部能力需要你协助提供 key：{missing_keys}。其余我会自动完成。”
- 执行确认：
  - “我已整理成可执行工作包，是否进入 dryrun / publish 门禁？”

## 交付检查
- 聊天气泡使用自然语言。
- 结构化内容只在工作包蓝图与轨迹区展示。
- `nanobot<->opencode` 轨迹可见且可审计。
