# Story EPIC4-S4：Runtime / API seam 收敛与主链边界清理

状态：ready-for-dev

## 用户故事

作为 `lane-02` owner，
我希望收敛 `services/governance_api/` 与 `services/governance_worker/` 的 seam，
以便主链运行边界清晰、测试口径稳定，并为后续控制层替换留出安全切口。

## owned surface

1. `services/governance_api/`
2. `services/governance_worker/`
3. `packages/agent_runtime/`
4. `packages/governance_runtime/`
5. 相关测试

## 依赖

1. `EPIC4-S1`
2. `EPIC4-S2`

## 验收标准

1. Runtime / API 的首轮 seam 收敛范围明确。
2. 主链边界清理不破坏现有 `workpackage executor` 执行面。
3. Router、service、worker 边界拆分切口可验证。
4. 不在本 Story 中夹带控制层整体语言替换。

## 最小测试 / 验收

1. 先补 seam 相关失败用例或最小检查单。
2. 运行 `lane-02` 最小测试集。

## Ring1 影响判断

1. 会影响 Runtime 组件文档，实施时需回填 `docs/04_系统组件设计/03_Runtime执行/`。
