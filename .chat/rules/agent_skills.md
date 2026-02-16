# Agent 能力与 Skill 链绑定

在执行任务时，必须遵循以下 Skill 链条：

1. **项目管理/看板/指标**: `project_orchestrator_v1`
   - 链条: `specify -> clarify -> tasks -> checklist`
   
2. **工程监理/审计**: `engineering_supervisor_v1`
   - 链条: `analyze -> checklist`

3. **核心引擎/可信Hub/地址规则**: `core_runtime_v1` / `trust_data_hub_v1`
   - 链条: `plan -> implement -> analyze`

4. **产线执行**: `line_execution_v1`
   - 链条: `tasks -> implement -> analyze`

5. **测试与质量**: `test_quality_gate_v1`
   - 链条: `tasks -> implement -> checklist`

**验收门禁**:
- 所有 Implement 必须有对应的 Test/Analyze 证据。
- NO_GO 状态下禁止合并代码。
