# Story EPIC15-S2：FactoryAgent façade 保持稳定并切换到新编排内核

状态：ready-for-dev

## 用户故事

作为 `lane-01` owner，
我希望保留 `FactoryAgent` façade 并在其背后切换到新的编排内核，
以便框架替换试点可以采用单向迁移方式推进，同时不打破 CLI、API 和现有测试的外部合同。

## owned surface

1. `packages/factory_agent/`
2. `packages/factory_cli/`
3. 相关测试
4. `docs/04_系统组件设计/01_工厂Agent编排/`

## 依赖

1. `EPIC15-S1`

## 验收标准

1. `FactoryAgent` 继续作为 façade 保持对外稳定入口。
2. 新编排内核的接线点明确，且默认发生在 façade 背后。
3. CLI、API、测试不直接穿透到新 graph 内核。
4. 旧编排链路不再作为长期并行实现保留。
5. 默认实现切换到新编排内核后，façade 对外合同保持稳定。

## 最小测试 / 验收

1. 先补 façade 稳定性相关测试或检查单。
2. 运行 `lane-01` 最小测试集。

## Ring1 影响判断

1. 会影响 Agent 组件设计，实施时需回填 `docs/04_系统组件设计/01_工厂Agent编排/`。
