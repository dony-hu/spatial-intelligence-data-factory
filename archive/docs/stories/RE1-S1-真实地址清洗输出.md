# Story: RE1-S1 真实地址清洗输出

## 目标

将当前随机清洗输出替换为真实清洗引擎输出。

## 验收标准

1. 输出包含 `standardized_address`。
2. 输出包含 `components.city/district/road/house_number`。
3. 输出包含 `confidence`。
4. 对无效输入输出失败码 `CLEANING_INVALID_OUTPUT`。

## 开发任务

1. 在 `tools/factory_agents.py` 实现真实清洗函数。
2. 将 `STANDARDIZATION` 步骤输出改为契约结构。
3. 增加单测覆盖有效与无效地址。

## 测试用例

1. `上海黄浦中山东路1号` -> 成功，字段完整。
2. 空字符串 -> 失败。
