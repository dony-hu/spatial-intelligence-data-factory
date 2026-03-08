# Story EPIC4-S3：Factory Agent 巨石拆分但保持外部契约不变

状态：ready-for-dev

## 用户故事

作为 `lane-01` owner，
我希望拆分 `packages/factory_agent/` 的内部结构，
以便后续框架替换和模块演进有稳定落点，同时不打破现有外部契约。

## owned surface

1. `packages/factory_agent/`
2. `packages/factory_cli/`
3. 相关测试
4. `docs/04_系统组件设计/01_工厂Agent编排/`

## 依赖

1. `EPIC4-S1`
2. `EPIC4-S2`

## 验收标准

1. façade、conversation、blueprint、trace、memory、publish/dryrun 协调逻辑的切分方案明确。
2. 外部正式契约保持不变。
3. 结构拆分切口可用最小测试集验证。
4. 不在本 Story 中夹带框架整体替换。

## 最小测试 / 验收

1. 先补结构边界相关测试或检查单。
2. 运行 `lane-01` 最小测试集。

## Ring1 影响判断

1. 会影响 Agent 组件文档，实施时需回填 `docs/04_系统组件设计/01_工厂Agent编排/`。
