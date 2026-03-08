# Story EPIC4-S1：共享契约冻结与消费基线固化

状态：ready-for-dev

## 用户故事

作为 `lane-03` 契约 owner，
我希望在首轮重构实施前冻结共享契约并明确唯一消费口径，
以便 Factory Agent、Runtime / API 与测试基线不会在过渡态中各自猜测接口。

## owned surface

1. `workpackage_schema/`
2. `contracts/`
3. `schemas/`
4. `docs/04_系统组件设计/02_工作包协议/`
5. `docs/99_研发过程管理/14_EPIC-重构实施基线落位/`

## 影响的共享契约

1. `workpackage_schema.v1`
2. `orchestration_context.v1`
3. Agent 与 Runtime 交接载荷
4. 数据库分域与迁移 owner 声明

## 验收标准

1. 形成首版共享契约冻结清单。
2. 每个共享契约对象都有唯一 owner 或串行变更路径。
3. 明确下游 Lane 的消费基线和禁止自行推导的边界。
4. 契约 PR 与实现 PR 的拆分规则明确。
5. 输出仅修改文档与契约说明，不直接混入业务实现迁移。

## 最小测试 / 验收

1. 人工检查清单
2. 契约文件路径核对
3. 下游消费说明核对

## Ring1 影响判断

1. 会影响 Ring1 正式协议文档，实施时需同步回填 `docs/04_系统组件设计/02_工作包协议/`。
