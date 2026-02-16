# PG-Only 全局数据库架构评审与迁移草案（V1）

日期：2026-02-16  
范围：`spatial-intelligence-data-factory` 全系统（Address 线 + Runtime 控制面 + Trust 数据域）

## 1. 目标与结论

本次评审以“彻底 PG-Only、降低复杂性、提升可演进性”为目标。  
结论如下：

1. 当前采用单库多 Schema（`address_line`、`control_plane`、`trust_meta`、`trust_db`）方向正确，符合“业务域隔离 + 运维简化”目标。
2. `source_snapshot` 使用全局主键 `snapshot_id` + 组合唯一键 `(namespace_id, snapshot_id)` 的建模存在不一致，应收敛为复合主键 `(namespace_id, snapshot_id)`。
3. `parsed_payload` 重复 DDL（建表 + ALTER）属于迁移策略混用导致的冗余，初始化脚本应保持“幂等且无重复定义”。

## 2. PG-Only 目标架构

单数据库：`si_factory`

- `address_line`：地址治理主链路（治理任务、审核、规则、审计、样本融合）
- `control_plane`：运行时控制面（队列、任务状态、运行证据、流程编排状态）
- `trust_meta`：可信源元数据（源注册、快照、质检、发布、回放）
- `trust_db`：可信实体索引（行政区、道路、POI、地名索引）

设计原则：

1. 跨域通过显式键关联，不做隐式耦合。
2. 所有“租户/命名空间隔离”表优先采用 `namespace_id` 前缀主键模型。
3. 控制面与业务面解耦：`control_plane` 不承载业务事实数据，只承载运行态与调度态。

## 3. 全局合理性审视（重点）

### 3.1 命名空间一致性

现状：

- 绝大部分 Trust 相关表已使用 `namespace_id`。
- `source_snapshot` 仍以 `snapshot_id` 作为单列主键。

风险：

1. 语义上把“全局唯一”强加到本应“命名空间内唯一”的实体。
2. 后续若引入多 namespace 并行回放，ID 复用策略受限。
3. 外键模型不统一，迁移和代码理解成本升高。

建议：

1. 统一采用 `(namespace_id, snapshot_id)` 作为主键与外键引用基准。
2. 对所有引用 `source_snapshot` 的表执行外键收敛。

### 3.2 控制面隔离

现状：

- `control_plane` 已独立 schema，方向正确。

建议：

1. 运行类 API 查询默认 `search_path` 包含 `control_plane`，避免误读业务表。
2. 禁止业务表反向依赖控制面表主键（只允许业务写事件到控制面日志流）。

### 3.3 Address 双线合并（Governance + Graph Sample）

现状：

- 已合并至 `address_line`，并通过兼容视图承接历史 `addr_*` 命名。

建议：

1. 兼容视图保留一个过渡周期（建议 1-2 个迭代），随后清理历史命名读路径。
2. 在 `address_line` 内建立“主事实表 + 衍生索引表”层次，减少重复写。

## 4. 对你提出两点建议的结论

### 建议 A：`source_snapshot` 改复合主键

结论：合理，且建议执行。  
优先级：P1（结构一致性）

### 建议 B：`parsed_payload` 重复定义清理

结论：合理，建议执行。  
优先级：P2（DDL 清洁度）

处理策略：

1. 基线初始化 SQL：仅保留建表定义。
2. 增量迁移 SQL：仅在历史环境需要“补列”时保留 `ADD COLUMN IF NOT EXISTS`。

## 5. 迁移草案（`source_snapshot` 主键重构）

以下为推荐迁移步骤（先灰度、后切主）：

1. 盘点依赖：
   - `trust_meta.snapshot_quality_report`
   - `trust_meta.snapshot_diff_report`
   - `trust_meta.active_release`
   - `trust_meta.validation_replay_run`
2. 为依赖表补齐/确认 `namespace_id` 非空约束。
3. 创建新主键并切换外键。
4. 删除旧主键与多余唯一键。

参考 SQL（需在迁移脚本中拆分为可回滚步骤）：

```sql
BEGIN;

-- 1) 删除引用 source_snapshot(snapshot_id) 的旧外键（名称以实际库为准）
ALTER TABLE trust_meta.snapshot_quality_report DROP CONSTRAINT IF EXISTS snapshot_quality_report_namespace_id_snapshot_id_fkey;
ALTER TABLE trust_meta.snapshot_diff_report DROP CONSTRAINT IF EXISTS snapshot_diff_report_namespace_id_base_snapshot_id_fkey;
ALTER TABLE trust_meta.snapshot_diff_report DROP CONSTRAINT IF EXISTS snapshot_diff_report_namespace_id_new_snapshot_id_fkey;
ALTER TABLE trust_meta.active_release DROP CONSTRAINT IF EXISTS active_release_namespace_id_active_snapshot_id_fkey;
ALTER TABLE trust_meta.validation_replay_run DROP CONSTRAINT IF EXISTS validation_replay_run_namespace_id_snapshot_id_fkey;

-- 2) source_snapshot 切复合主键
ALTER TABLE trust_meta.source_snapshot DROP CONSTRAINT IF EXISTS source_snapshot_pkey;
ALTER TABLE trust_meta.source_snapshot ADD CONSTRAINT source_snapshot_pkey PRIMARY KEY (namespace_id, snapshot_id);
ALTER TABLE trust_meta.source_snapshot DROP CONSTRAINT IF EXISTS source_snapshot_namespace_id_snapshot_id_key;

-- 3) 重新建立复合外键
ALTER TABLE trust_meta.snapshot_quality_report
  ADD CONSTRAINT snapshot_quality_report_namespace_id_snapshot_id_fkey
  FOREIGN KEY (namespace_id, snapshot_id)
  REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id);

ALTER TABLE trust_meta.snapshot_diff_report
  ADD CONSTRAINT snapshot_diff_report_namespace_id_base_snapshot_id_fkey
  FOREIGN KEY (namespace_id, base_snapshot_id)
  REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id);

ALTER TABLE trust_meta.snapshot_diff_report
  ADD CONSTRAINT snapshot_diff_report_namespace_id_new_snapshot_id_fkey
  FOREIGN KEY (namespace_id, new_snapshot_id)
  REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id);

ALTER TABLE trust_meta.active_release
  ADD CONSTRAINT active_release_namespace_id_active_snapshot_id_fkey
  FOREIGN KEY (namespace_id, active_snapshot_id)
  REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id);

ALTER TABLE trust_meta.validation_replay_run
  ADD CONSTRAINT validation_replay_run_namespace_id_snapshot_id_fkey
  FOREIGN KEY (namespace_id, snapshot_id)
  REFERENCES trust_meta.source_snapshot(namespace_id, snapshot_id);

COMMIT;
```

## 6. 后续建议（全局）

1. 统一迁移入口：所有结构变更只走 migration（禁止“初始化 SQL + 运行期 SQL”双写同一变更）。
2. 统一键策略文档化：在 `docs` 增加“ID 与主键规范”页，明确哪些实体是全局键、哪些是 namespace 键。
3. 增加结构一致性 CI：
   - 校验 `PRIMARY KEY` 与外键引用一致性；
   - 校验无重复列定义；
   - 校验 schema 之间禁止反向耦合规则。

