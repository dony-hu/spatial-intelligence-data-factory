# 架构设计：真实地址执行链路（2026-02-12）

## 1. 设计目标

1. 单 case = 单条地址输入。
2. 流程语义与业务语义一致：仅当产物门禁通过才 `completed`。
3. 清洗与图谱均输出真实产物，不再依赖随机模拟结果。

## 2. 输入输出契约

## 2.1 输入契约（CaseInput）

```json
{
  "case_id": "string",
  "raw_address": "string",
  "source": "string"
}
```

## 2.2 清洗输出契约（CleaningOutput）

```json
{
  "standardized_address": "string",
  "components": {
    "city": "string",
    "district": "string",
    "road": "string",
    "house_number": "string"
  },
  "confidence": 0.0
}
```

## 2.3 图谱输出契约（GraphOutput）

```json
{
  "nodes": [
    {
      "node_id": "string",
      "node_type": "string",
      "name": "string",
      "properties": {}
    }
  ],
  "relationships": [
    {
      "relationship_id": "string",
      "source_node_id": "string",
      "target_node_id": "string",
      "relationship_type": "string"
    }
  ]
}
```

## 3. 执行链路

`CaseInput -> CleaningEngine -> CleaningGate -> GraphEngine -> GraphGate -> StateTransition`

## 3.1 CleaningGate

通过条件：

1. `standardized_address` 非空
2. `components.city/district/road/house_number` 全部存在
3. `confidence >= threshold`（默认 0.7）

失败：进入 `FAILED`，记录错误码 `CLEANING_INVALID_OUTPUT`

## 3.2 GraphGate

通过条件：

1. `nodes.length > 0`
2. `relationships.length > 0`

失败：进入 `FAILED`，记录错误码 `GRAPH_EMPTY_OUTPUT`

## 4. 状态机语义

1. `EXECUTING` 仅表示流程在跑。
2. `COMPLETED` 必须在 `CleaningGate + GraphGate` 全通过后触发。
3. 失败不重试（按确认口径）。

## 5. 证据链（Evidence）

每条 case 必须写入：

1. 输入摘要（raw_address/source）
2. 清洗输出摘要（standardized_address/components/confidence）
3. 图谱输出摘要（nodes_count/relationships_count）
4. Gate 结果（pass/fail + reason）
5. 最终状态

## 6. 看板数据模型

动态列表项结构：

```json
{
  "case_id": "string",
  "line_owner": "地址清洗产线 + 地址-图谱产线",
  "input": {},
  "cleaning_output": {},
  "graph_output": {},
  "gate_result": {},
  "status": "completed|failed",
  "timestamp": "iso"
}
```

弹框分区：

1. 输入
2. 清洗输出
3. 图谱输出 + 门禁结果

## 7. 模块改造点

1. `tools/factory_agents.py`
- 替换 `Worker.execute_task` 中随机输出逻辑
- 接入真实清洗函数与真实图谱构建函数

2. `tools/factory_workflow.py`
- 新增 Gate 检查与失败语义
- 仅 Gate 通过时更新 `completed`

3. `scripts/factory_continuous_demo_web.py`
- 详情数据改为结构化输入/输出/gate

4. `templates/dashboard.html`
- 详情弹框结构化渲染

## 8. 验收标准

1. `quick_test` 每条 case 清洗成功。
2. `quick_test` 每条 case 图谱 `nodes>0 && relationships>0`。
3. 不允许出现 `completed` 且图谱产物为空。
4. 看板可查看每条 case 的完整输入与产线输出。
