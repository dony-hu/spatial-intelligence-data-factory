# 评测样例扩展计划（性能/成本/回归）

日期：2026-02-14

## 1. 目标

1. 在现有功能正确性样例基础上补齐性能、成本、回归三类评测。
2. 建立 P0/P1/P2 分层基线，明确 CI 与定时回归职责。
3. 让“空产物却 completed”等关键回归在自动化中可阻断。

## 2. 样例分层

1. `P0`（提交阻断）  
说明：小样本、快执行、强语义门禁。  
建议数量：20~50 cases。

2. `P1`（日常回归）  
说明：中样本、覆盖异常路径与回放路径。  
建议数量：200~500 cases。

3. `P2`（压测/成本）  
说明：大样本、稳定性与成本阈值评估。  
建议数量：1000+ cases。

## 3. 数据集规划

| 数据集 ID | 优先级 | 目标 | 来源 | 备注 |
|---|---|---|---|---|
| `geo_addr_smoke_p0_v2026.02.14` | P0 | 清洗+图谱主链路门禁 | `testdata/fixtures/*samples.json` | 作为 CI 阻断 |
| `geo_addr_regression_p1_v2026.02.14` | P1 | 失败分支与 replay 回归 | `output/line_runs/failed_replay_queue.json` + 固化样例 | 每日回归 |
| `geo_addr_perf_p2_v2026.02.14` | P2 | 吞吐、延迟、成本基线 | `testdata/fixtures/address-graph-cases-1000-2026-02-12.json` | 周期压测 |

## 4. 指标与阈值（首版）

1. 功能正确性  
- `graph_nodes_count >= 1`（有效地址）
- `completed` 与门禁结果一致

2. 性能  
- P0：单 case `p95 <= 2s`
- P1：批量 `p95 <= 5s`
- P2：1000 cases 总时长 <= 30min

3. 成本  
- 单 case token 成本阈值（按模型定价配置）
- 失败重试次数上限（默认 3）

## 5. 自动化接入

1. CI（P0）  
- 提交触发：schema + quick_test + `geo_addr_smoke_p0`
- 失败即阻断合并

2. 定时回归（P1）  
- 每日执行 `geo_addr_regression_p1`
- 失败自动生成缺陷记录

3. 周期压测（P2）  
- 每周执行 `geo_addr_perf_p2`
- 输出性能与成本趋势报告

## 6. 本周交付清单

1. 新增 `P0` 与 `P1` 样例集元数据到 `testdata/catalog.yaml`。  
2. 补齐回放链路样例固化脚本（读取 `failed_replay_queue`）。  
3. 新增至少 2 条评测测试：  
- 性能阈值测试  
- 成本阈值测试（可先 mock）
