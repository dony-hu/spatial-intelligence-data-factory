# 工艺流程文档：工具包生成工艺（修改版）

- **process_code**: `PROC_TOOLPACK_BOOTSTRAP`
- **change_request**: { "iteration_round": 2, "prioritized_repair_target": "P1级缺口story_token_graph_chain_present", "repair_actions": [ "调用可信接口fengtu/address_standardize（地址标准化）、fengtu/address_resolve_l5（五级地址解析）补全地址分词-图谱链路过程", "通过通用修复补齐story_standardized_completion_with_street缺口的街道字段" ], "evidence_checklist": { "story_token_graph_chain_present": ["分词结果", "链路说明"], "story_standardized_completion_with_street": ["修复说明"] }, "
- **goal**: 提升工艺文档质量与工具脚本完备度
- **auto_execute**: False

## 修改步骤

1. 地图API采样
2. LLM归并别名
3. 工具包脚本生成
4. 质量审计回放

## 配置信息

| 配置项 | 值 |
| ---- | ---- |
| 执行优先级 | 1 |
| 最大执行时长 | 1200s |
| 质量阈值 | 0.9 |