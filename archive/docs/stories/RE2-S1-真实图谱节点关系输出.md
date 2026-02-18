# Story: RE2-S1 真实图谱节点关系输出

## 目标

基于清洗结果生成真实图谱节点与关系。

## 验收标准

1. `nodes.length > 0`。
2. `relationships.length > 0`。
3. 节点包含 `node_id/node_type/name/properties`。
4. 关系包含 `relationship_id/source_node_id/target_node_id/relationship_type`。

## 开发任务

1. 在 `tools/factory_agents.py` 图谱步骤生成节点与关系。
2. 在 `tools/factory_workflow.py` 落库存储节点与关系。
3. 增加单测验证产物数量与字段完整性。
