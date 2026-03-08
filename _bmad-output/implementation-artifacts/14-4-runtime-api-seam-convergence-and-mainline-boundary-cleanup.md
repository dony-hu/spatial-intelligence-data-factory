# Story 14.4 - Runtime / API seam 收敛与主链边界清理

Status: ready-for-dev

## 目标

收敛 `services/governance_api/` 与 `services/governance_worker/` 的 seam，并清理主链边界。

## 验收标准

1. Runtime / API 的首轮 seam 收敛范围明确。
2. 主链边界清理不破坏现有 `workpackage executor` 执行面。
3. Router、service、worker 边界拆分切口可验证。
4. 不在本 Story 中夹带控制层整体语言替换。

## Tasks

- [ ] T1: 补 seam 相关失败用例或最小检查单
- [ ] T2: 收敛 router/service/worker 边界
- [ ] T3: 运行最小测试集并记录影响面

