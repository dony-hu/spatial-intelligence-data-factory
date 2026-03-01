# Story：OBS-RUNTIME-S2-10 运行态 API 测试闭环与旧 lab 兼容降级

## 1. 目标

完成 `runtime/*` API 的可执行测试闭环，并将旧 `lab/observability/*` 测试降级为兼容层验证，避免主线测试口径混乱。

## 2. 范围

1. `runtime/summary|risk-distribution|version-compare|tasks` 契约测试常态化。
2. 旧 `lab` 观测接口测试标记为兼容层（compat），不作为主验收口径。
3. 增加路由存在性守卫测试，防止回归为 404。

## 3. 验收标准

1. 运行态 API 契约测试可稳定执行并纳入主线。
2. 主线验收报告明确区分 `runtime` 与 `lab`。
3. 旧 `lab` 用例不阻塞运行态上线判定。

## 4. 测试要求（TDD）

1. 先补失败用例（当前 404 基线）。
2. 再实现路由与服务。
3. 最后回归并输出证据。
