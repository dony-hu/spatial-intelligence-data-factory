# Iteration-002 Core Engine P0 拆解派单

- 日期：2026-02-15
- 目标：将 P0 稳定化总包拆分为 A/B/C 三个可并行执行、可独立验收、可独立回滚的工作包
- 总控门槛：统一 Python 3.11+、R2 门槛闭环、形成 GO/NO_GO 判定

## 工作包与边界

1. 包 A：Address Core 算法与测试
- 文件：`workpackages/wp-core-engine-address-core-p0-v0.1.0.json`
- 目录边界：`packages/address_core/`
- 关键产出：算法收敛、模块单测与 smoke 基线、兼容性报告
- 依赖：无前置硬依赖，可立即启动

2. 包 B：Governance API + Lab
- 文件：`workpackages/wp-core-engine-governance-api-lab-p0-v0.1.0.json`
- 目录边界：`services/governance_api/`（允许关联契约与迁移脚本）
- 关键产出：Python 3.11+ 运行时收敛、审批硬门控、观测回归
- 依赖：需与总控统一运行时基线同步

3. 包 C：Trust Data Hub
- 文件：`workpackages/wp-core-engine-trust-data-hub-p0-v0.1.0.json`
- 目录边界：`services/trust_data_hub/` + `database/trust_meta_schema.sql`
- 关键产出：仓储持久化接线、fetch/parse 稳态、replay 证据契约
- 依赖：可并行启动；联调阶段需与 B 的 validate 契约对齐

## 并行策略

1. Day 1：A/B/C 同步启动，先冻结各自测试基线与失败样本。
2. Day 2：A 做算法收敛，B 做运行时与门禁修复，C 做仓储接线。
3. Day 3：B/C 完成 API 契约联调，A 交付兼容性报告。
4. Day 4：统一回归与发布判定，输出 GO/NO_GO 与回滚预案。

## 统一验收清单

1. 三包各自测试命令与结果可复现。
2. 三包均输出 `done/next/blocker/eta/test_report_ref`。
3. 工作包、观测包、产线回传字段格式一致。
4. 任一包失败可单独回滚，不阻塞其他包收敛。
