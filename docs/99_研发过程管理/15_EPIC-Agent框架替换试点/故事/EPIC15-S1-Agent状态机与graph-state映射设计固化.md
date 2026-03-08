# Story EPIC15-S1：Agent 状态机与 graph state 映射设计固化

状态：ready-for-dev

## 用户故事

作为 Agent 编排层替换试点的设计 owner，
我希望先把正式状态集合与 `graph state` 的映射关系固化，
以便后续 `LangGraph` 试点实现不会在状态、记忆对象和人机中断语义上各自发明口径。

## owned surface

1. `docs/99_研发过程管理/15_EPIC-Agent框架替换试点/`
2. `docs/04_系统组件设计/01_工厂Agent编排/`
3. `workpackage_schema/schemas/v1/`
4. `workpackage_schema/examples/v1/`

## 影响的共享契约

1. 正式状态集合
2. `orchestration_context.v1`
3. Agent 与 Runtime 交接载荷
4. human gate / blocked / recover 语义

## 验收标准

1. `DISCOVERY` 到 `COMPLETED` 的正式状态集合有明确 graph state 映射。
2. `WAIT_USER_INPUT / WAIT_USER_GATE / BLOCKED` 的语义有明确 interrupt / approval / recover 映射。
3. `orchestration_context.v1` 中被 graph state 消费和回写的字段清单明确。
4. 明确哪些状态和字段属于首批试点范围，哪些留待后续 Story。
5. 输出不混入具体业务代码迁移。

## 最小测试 / 验收

1. 人工检查清单
2. 状态映射表核对
3. `orchestration_context.v1` 字段核对

## Ring1 影响判断

1. 会影响 Agent 编排正式设计，实施时需同步回填 `docs/04_系统组件设计/01_工厂Agent编排/`。
