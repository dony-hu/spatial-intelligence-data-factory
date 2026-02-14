# 工艺件：完整工艺流程记录

- 用例总量: 16
- 轮次数: 1

## 全局文字描述

本工作包记录了基于地址用例的工艺生成与迭代过程，覆盖设计、修改、审计以及脚本产物。

## Round 1 (design)

- 工艺编码: `PROC_TOOLPACK_BOOTSTRAP`
- 审计得分: 0.8181818181818182
- 草案ID: `draft_b025f0c068`

### 关键条件判断
- `status_ok`: 通过
- `compile_success`: 通过
- `has_process_spec`: 通过
- `has_tool_scripts`: 通过
- `doc_length_ok`: 通过
- `contains_iteration_keywords`: 通过
- `plan_steps_ok`: 通过
- `story_authenticity_two_trusted_sources`: 通过
- `story_standardized_completion_with_street`: 未通过
- `story_token_graph_chain_present`: 未通过
- `story_clear_conclusion`: 通过

### Story审计要求结果确认
- `R1_authenticity_two_trusted_interfaces` 真实性确认必须来自至少两个可信接口: 通过（已明确）
- `R2_standardization_with_street` 标准化补齐结果必须包含街道: 未通过（未明确）
- `R3_tokenization_graph_chain` 必须包含地址标准化分词拆解并形成图谱链: 未通过（未明确）

### 调用脚本与说明
- `address_validator`: 地址验证器 - 自动生成
- `address_normalizer`: 地址规范化器 - 自动生成
- `quality_evaluator`: 质量评估器 - 自动生成
- `data_generator`: 数据生成器 - 自动生成
- `db_persister`: 数据库持久化器 - 自动生成

