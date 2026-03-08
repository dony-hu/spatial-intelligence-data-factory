# Story EPIC15-S3：Discovery / Align IO / Blueprint Loop 试点迁移

状态：ready-for-dev

## 用户故事

作为 `lane-01` owner，
我希望先迁移 `DISCOVERY / ALIGN_IO / BLUEPRINT_LOOP` 这三段主流程，
以便用最稳定的状态切片验证 `LangGraph + PydanticAI + nanobot adapter` 的新骨架是否可行。

## owned surface

1. `packages/factory_agent/`
2. `packages/factory_cli/`
3. 相关测试
4. `docs/04_系统组件设计/01_工厂Agent编排/`

## 依赖

1. `EPIC15-S1`
2. `EPIC15-S2`

## 验收标准

1. `DISCOVERY / ALIGN_IO / BLUEPRINT_LOOP` 已在新编排内核中落位。
2. `PydanticAI` 已承接首批 typed output / tool 调用语义。
3. `nanobot` 在该试点范围内仅作为模型 / Provider 访问 adapter。
4. façade 对外合同保持稳定，内部默认切换到新编排内核。
5. 不在本 Story 中提前迁移 `BUILD_WITH_OPENCODE / VERIFY / PUBLISH`。
6. 不为旧编排链路保留切换机制。

## 最小测试 / 验收

1. requirement query 合同测试
2. general governance chat 合同测试
3. blueprint generation 合同测试
4. `lane-01` 最小测试集

## Ring1 影响判断

1. 会影响 Agent 编排正式设计，实施时需回填 `docs/04_系统组件设计/01_工厂Agent编排/`。
