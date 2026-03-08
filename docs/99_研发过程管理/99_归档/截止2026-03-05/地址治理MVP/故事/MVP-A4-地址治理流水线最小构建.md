# Story: MVP-A4 地址治理流水线最小构建

## 目标

基于 MVP 工作包构建一条最小地址治理流水线，覆盖输入、清洗治理、结果输出与证据记录。

## 验收标准

1. 流水线可处理最小样例地址集并生成治理结果。
2. 结果包含 `strategy/confidence/evidence` 关键字段。
3. 失败记录有明确语义并可回放。
4. 流水线执行产物可被 Runtime 与看板消费，且异常路径不允许 fallback，必须阻塞上报。

## 开发任务

1. 先补测试：最小样例集通过与异常输入失败用例。
2. 再改实现：补齐流水线入口与输出契约绑定。
3. 最后验证：产出运行报告与样例结果集。

## 测试用例

1. 正常地址输入输出结构化治理结果。
2. 空地址输入返回失败并记录原因。

## 对齐信息（PRD/架构）

1. PRD 对齐：EPIC A（治理主链路）+ EPIC C（可观测交付）。
2. 架构对齐：
- `docs/02_总体架构/系统总览.md` 治理试运行流/发布执行流。
- `docs/02_总体架构/模块边界.md` Core 与 Trust 查询边界。

## 模块边界与 API 边界

1. 所属模块：`address_core`、`runtime worker`、`governance repository`、`observability`。
2. 上游入口：Runtime 任务执行触发。
3. 下游依赖：治理核心流程、结果持久化、审计/观测输出。
4. API 边界：对外仅暴露结果契约，不透出内部流水线步骤实现细节。

## 依赖与禁止耦合

1. 允许依赖：`runtime worker -> address_core -> repository/trust query interface`。
2. 禁止耦合：
- `address_core` 直接依赖 FastAPI request/response。
- 失败链路使用默认结果对象伪装成功。
