# Story: RE3-S2 证据链结构化摘要

## 目标

每条 case 都可追踪输入、清洗输出、图谱输出、门禁结果。

## 验收标准

1. Evidence 包含输入摘要。
2. Evidence 包含清洗输出摘要。
3. Evidence 包含图谱产物计数与门禁结果。
4. 可通过 case_id 回放执行路径。

## 开发任务

1. 扩展 `scripts/factory_continuous_demo_web.py` 详情结构。
2. 扩展 runtime evidence 记录字段。
3. 增加 case 回放检查脚本/测试。
