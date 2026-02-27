# Architecture - 统一 PostgreSQL 多 Schema 设计方案（v1）

## 1. 文档信息

- 文档版本：v1.0
- 创建日期：2026-02-27
- 所属阶段：BMAD Solutioning / Architecture
- 关联决策：
  1. 统一到 PostgreSQL 单实例单数据库。
  2. 用 schema 区分不同领域。
  3. 保留历史快照，按 active release 控制查询口径。
- 文档语言：中文（遵循仓库 AGENTS 规则）

## 2. 目标与范围

### 2.1 目标

1. 清理当前“多套 schema 真相”问题，形成单一演进路径。
2. 降低运行时漂移风险，保证测试环境与生产环境一致。
3. 为治理主链路、Runtime 发布、Trust Hub 提供稳定的数据边界。

### 2.2 范围

1. 数据库逻辑结构重组（schema、表、主外键、索引策略）。
2. 迁移策略与落地顺序。
3. 仓储层读写与审计规范。

不在本方案范围：

1. 业务 API 契约重写。
2. 数据权限体系（多租户/RLS）深度设计。

## 3. 统一数据库拓扑

- 实例：一个 PostgreSQL 实例。
- 数据库：一个逻辑数据库（建议 `sidf`）。
- schema：
  1. `governance`：地址治理主链路。
  2. `runtime`：工作包发布与运行态。
  3. `trust_meta`：可信数据元信息与快照管理。
  4. `trust_data`：可信检索数据。
  5. `audit`：统一审计事件。

## 4. 领域模型设计

### 4.1 governance（治理主链路）

核心表：

1. `governance.batch`
2. `governance.task_run`
3. `governance.raw_record`
4. `governance.canonical_record`
5. `governance.review`
6. `governance.ruleset`
7. `governance.change_request`

关键约束：

1. `task_run.status` 采用 CHECK 约束：`PENDING/RUNNING/SUCCEEDED/FAILED/BLOCKED/REVIEWED`。
2. `canonical_record` 要求 `strategy/confidence/evidence` 非空（或可推导非空）。
3. `review.review_status` 采用 CHECK：`approved/rejected/edited`。

### 4.2 runtime（发布与运行态）

核心表：

1. `runtime.workpackage`
2. `runtime.workpackage_version`
3. `runtime.publish_record`
4. `runtime.deployment_event`

关键约束：

1. 发布唯一键：`(workpackage_id, version)`。
2. 状态 CHECK：`draft/blocked/published/rolled_back`。
3. `publish_record.evidence_ref` 必填，禁止“无证据成功”。

### 4.3 trust_meta（可信元数据）

核心表：

1. `trust_meta.source_registry`
2. `trust_meta.source_schedule`
3. `trust_meta.source_snapshot`
4. `trust_meta.quality_report`
5. `trust_meta.diff_report`
6. `trust_meta.active_release`
7. `trust_meta.validation_replay_run`

关键约束：

1. `source_snapshot` 主键：`(namespace_id, source_id, snapshot_id)`。
2. `active_release` 主键：`(namespace_id, source_id)`。
3. `active_release(namespace_id, source_id, active_snapshot_id)` 必须 FK 指向 `source_snapshot(namespace_id, source_id, snapshot_id)`，避免 source 与 snapshot 错配。
4. replay 记录保留请求与结果摘要，支持按 snapshot 回放审计。

### 4.4 trust_data（可信检索数据）

核心表：

1. `trust_data.admin_division`
2. `trust_data.road_index`
3. `trust_data.poi_index`
4. `trust_data.place_name_index`

关键约束：

1. 所有主表均包含 `namespace_id/source_id/snapshot_id` 维度。
2. 历史快照保留，不做“按 source 全删重灌”。
3. 查询层默认通过 `trust_meta.active_release` 过滤当前生效快照。

### 4.5 audit（统一审计）

核心表：

1. `audit.event_log`

关键字段：

1. `event_id`
2. `domain`（governance/runtime/trust_meta/trust_data）
3. `event_type`
4. `actor`
5. `trace_id`
6. `target_ref`
7. `payload_json`
8. `created_at`

说明：将现有分散审计事件逐步汇聚到统一审计表，保留领域字段便于检索。

## 5. ID 与时间字段规范

1. 全库主业务 ID 统一 `UUID`（`uuid` 类型）；外部业务主键可保留 `TEXT`，但需唯一约束。
2. 时间字段统一 `TIMESTAMPTZ`，禁止 `TEXT timestamp`。
3. 所有表必须包含 `created_at`，需要状态流转的表增加 `updated_at`。

## 6. 索引策略（最小必需）

1. `governance.task_run(status, updated_at DESC)`。
2. `runtime.publish_record(workpackage_id, version)` 唯一索引。
3. `trust_meta.source_snapshot(namespace_id, source_id, fetched_at DESC)`。
4. `trust_meta.validation_replay_run(namespace_id, snapshot_id, created_at DESC)`。
5. 名称检索字段（road/poi/place）采用 trigram GIN 索引。

## 7. 演进与迁移策略

### 7.1 单一真相原则

1. Alembic 作为唯一 schema 变更入口。
2. 下线/冻结运行时建表逻辑与独立 SQL 直刷脚本（仅保留只读校验脚本）。

### 7.2 迁移阶段

1. Phase A：创建新 schema 与基线表结构（不切流量）。
2. Phase B：数据回填（旧表 -> 新 schema），双写校验。
3. Phase C：仓储层切换到新 schema 全限定表名。
4. Phase D：移除旧表访问与 runtime 自动建表。
5. Phase E：执行回归与一致性验收，完成收口。

### 7.3 验收标准

1. 同一业务查询在旧链路与新链路结果一致。
2. active release 查询路径稳定，历史快照可追溯。
3. 迁移后无 runtime 建表语句。
4. CI 包含 schema 漂移检查并通过。

## 8. 风险与缓解

1. 风险：迁移期间数据口径偏差。
- 缓解：双写期增加对账脚本和抽样比对。

2. 风险：跨 schema 外键导致性能波动。
- 缓解：仅对关键一致性关系保留 FK，其余以应用侧约束+审计保证。

3. 风险：历史脚本仍可能绕过迁移入口。
- 缓解：CI 阻断非 Alembic DDL 变更。

## 9. 下一步输出（Implementation 输入）

1. 输出 Alembic 基线迁移（5 个 schema + 核心表）。
2. 输出数据迁移脚本（批次回填 + 校验）。
3. 输出 Story 拆解：
- S-DB-01 基线 schema 建设
- S-DB-02 Trust Meta 对齐
- S-DB-03 Runtime 发布域切换
- S-DB-04 审计统一与回归
