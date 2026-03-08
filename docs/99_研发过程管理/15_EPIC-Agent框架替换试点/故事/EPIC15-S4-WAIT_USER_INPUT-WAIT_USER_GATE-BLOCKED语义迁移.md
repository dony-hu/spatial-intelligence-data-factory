# Story EPIC15-S4：WAIT_USER_INPUT / WAIT_USER_GATE / BLOCKED 语义迁移

状态：ready-for-dev

## 用户故事

作为 Agent 框架替换试点的 owner，
我希望把 `WAIT_USER_INPUT / WAIT_USER_GATE / BLOCKED` 显式迁移到新的 interrupt / approval / recover 语义，
以便人机中断、阻塞和恢复逻辑继续保持正式工程语义，而不是回退到自然语言等待。

## owned surface

1. `packages/factory_agent/`
2. 相关测试
3. `docs/04_系统组件设计/01_工厂Agent编排/`
4. `docs/04_系统组件设计/03_Runtime执行/`

## 依赖

1. `EPIC15-S2`
2. `EPIC15-S3`

## 验收标准

1. `WAIT_USER_INPUT` 有明确 interrupt 语义映射。
2. `WAIT_USER_GATE` 有明确 approval 语义映射。
3. `BLOCKED` 保持显式原因、恢复点和结构化输出。
4. dryrun / publish 相关门禁语义与当前正式交接契约不冲突。
5. 不把阻塞和恢复逻辑重新塞回自由文本提示。

## 最小测试 / 验收

1. human gate 合同测试
2. blocked / recover 合同测试
3. dryrun / publish 触发相关最小测试

## Ring1 影响判断

1. 会影响 Agent 状态机与交接契约，实施时需回填：
   - `docs/04_系统组件设计/01_工厂Agent编排/`
   - `docs/04_系统组件设计/03_Runtime执行/`
