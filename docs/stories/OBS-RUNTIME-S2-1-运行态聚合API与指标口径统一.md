# Story：OBS-RUNTIME-S2-1 运行态聚合 API 与指标口径统一

## 1. 目标

交付运行态聚合 API，统一指标口径，确保前端不再自行计算核心指标。

## 2. 范围

1. `GET /v1/governance/observability/runtime/summary`
2. `GET /v1/governance/observability/runtime/risk-distribution`
3. `GET /v1/governance/observability/runtime/version-compare`
4. `GET /v1/governance/observability/runtime/tasks`
5. 指标口径统一：完成率、阻塞率、人工介入率、平均置信度

## 3. 验收标准

1. 四个 API 在 24h 窗口可返回结构化数据。
2. 同一筛选条件下，卡片与列表数据一致。
3. 指标计算结果与口径定义一致。
4. 数据不足时返回空态结构，不返回 500。
5. 关键数据源不可用时返回显式 `blocked/error`。

## 4. 测试要求（TDD）

1. 先补失败用例：
   - API 契约测试
   - 指标口径测试
   - No-Fallback 错误语义测试
2. 再实现接口与聚合逻辑。
3. 最后回归全通过并输出证据。

## 5. 依赖

1. PG 多 schema 运行库可用。
2. 观测仓储读模型已对齐当前 schema。
