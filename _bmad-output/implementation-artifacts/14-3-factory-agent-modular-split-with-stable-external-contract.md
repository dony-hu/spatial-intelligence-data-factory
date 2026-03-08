# Story 14.3 - Factory Agent 巨石拆分但保持外部契约不变

Status: ready-for-dev

## 目标

拆分 `packages/factory_agent/` 的内部结构，同时保持外部正式契约稳定。

## 验收标准

1. façade、conversation、blueprint、trace、memory、publish/dryrun 协调逻辑的切分方案明确。
2. 外部正式契约保持不变。
3. 结构拆分切口可用最小测试集验证。
4. 不在本 Story 中夹带框架整体替换。

## Tasks

- [ ] T1: 补结构拆分切口的失败用例或检查单
- [ ] T2: 调整模块边界与文件归属
- [ ] T3: 运行最小测试集并记录影响契约

