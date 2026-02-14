# L2 工厂可观测性规范

## 目标

观测工艺Agent、工具包、执行引擎的研发迭代闭环。

## 迭代链路

需求 -> 工艺草案 -> 编译 -> 校验 -> 发布 -> 下发 WorkPackage

## 核心指标

- 工艺版本迭代周期
- 工具/引擎版本兼容率
- 回滚次数与原因
- 需求到发布耗时

## 必留痕字段

- process_version
- tool_bundle_version
- engine_version
- change_reason
- released_at
