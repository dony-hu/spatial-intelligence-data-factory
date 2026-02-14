# 子线状态：工厂-工作包编译与下发

- 进度：90%
- Done：
  - 已切换为 `Factory-WorkPackage` 执行模式（仅处理工作包编译与下发）
  - TC-04 任务卡已编译并下发（版本：`TC-04-R1`）
  - `WorkPackage v1` 契约与模板已建立
  - 已产出首个实包：`wp-address-topology-v1.0.1.json`
  - 已恢复 TC-04 并进入 5 分钟自治循环执行
  - 已发布 `workpackages/wp-address-topology-v1.0.2.json`
  - 已完善下发元信息：`published_by`、`published_at`、`rollback_version`、`ticket_id`、`dispatch_status`
  - 已补齐 `workpackages/bundles/address-topology-v1.0.2/observability/*` 发布目录
  - 已完成 schema 基础校验（required/additionalProperties）
- Next：
  - 接入产线执行回执（`status`、`duration_ms`、`error_code`）并回填验收
  - 完成一次 `v1.0.2` 实跑抽样验证并固化发布说明
  - 准备 `TC-04-R2`（仅当回执出现字段缺口时）
- Blocker：无
- ETA：2026-02-14 12:00（本地时间，完成回执闭环）

## 任务卡：TC-04（工作包编译与下发）

- 卡号：`TC-04-R1`
- 范围：仅包含工作包编译、版本封装、下发与回执跟踪
- 输入：
  - `contracts/workpackage.schema.json`
  - `workpackages/wp-template-v1.json`
  - 产线字段对齐需求（address-topology）
- 输出：
  - `workpackages/wp-address-topology-v1.0.2.json`
  - 下发记录（发布人、发布时间、回滚版本）
  - 执行回执（状态、耗时、异常）
- 验收标准：
  - 通过 schema 校验
  - 产线回传字段 100% 对齐
  - 下发与回执记录完整可追溯
- 截止：2026-02-14 20:00（本地时间）
- 状态：执行中（`v1.0.2` 已发布，待回执闭环）

- Artifacts：
  - `contracts/workpackage.schema.json`
  - `workpackages/wp-template-v1.json`
  - `workpackages/wp-address-topology-v1.0.1.json`
  - `workpackages/wp-address-topology-v1.0.2.json`
  - `workpackages/bundles/address-topology-v1.0.2/observability/line_observe.py`
  - `workpackages/bundles/address-topology-v1.0.2/observability/line_metrics.json`
