# 联调记录：可信数据Hub replay持久化闭环（dispatch-address-line-closure-004）

- date: 2026-02-15
- timezone: Asia/Shanghai (CST)
- author: 可信数据Hub线-Codex
- role: 可信数据Hub线执行负责人
- work_items:
  - 打通 replay 持久化链路（Postgres）
  - 校对证据映射字段并兼容地址治理产线契约
  - 输出联调记录并同步状态回写
- deliverables:
  - `services/trust_data_hub/app/repositories/trust_repository.py`
  - `services/trust_data_hub/app/repositories/metadb_persister.py`
  - `services/trust_data_hub/app/routers/validation.py`
  - `services/trust_data_hub/app/routers/admin.py`
  - `services/trust_data_hub/app/models/trust_models.py`
  - `database/trust_meta_schema.sql`
  - `services/trust_data_hub/tests/test_trust_data_hub_api.py`
- risks:
  - 当前自动化测试主要覆盖仓储层 mock 与接口契约，真实 Postgres 容器未在本次执行中启动验证。
  - replay 持久化表为新增结构，若线上 schema 未迁移会导致 `replay_persist_failed`。
- next_actions:
  - 在 docker-compose Postgres 环境执行真实联调：创建 schema -> replay 请求 -> replay-runs 查询 -> SQL 核验。
  - 补充地址治理服务端到端调用样本，验证 `evidence.items` 下游消费一致性。
- evidence_links:
  - `database/trust_meta_schema.sql`
  - `services/trust_data_hub/tests/test_trust_data_hub_api.py`
  - `coordination/status/trust-data-hub.md`
- updated_at: 2026-02-15T23:55:00+08:00

## 1) replay 持久化链路打通（已完成）

- `POST /v1/trust/validation/replay` 已切换到 `replay_validation_evidence_by_snapshot`。
- 每次 replay 生成 `replay_id`、`replayed_at`，并返回 `storage_backend`（`postgres`/`memory`）。
- Postgres 模式下写入 `trust_meta.validation_replay_run`，字段包括：
  - `namespace_id`
  - `replay_id`
  - `snapshot_id`
  - `request_payload`
  - `replay_result`
  - `schema_version`
  - `created_at`
- 管理接口新增：
  - `GET /v1/trust/admin/namespaces/{namespace}/validation/replay-runs?snapshot_id=...&limit=...`

## 2) 证据映射字段校对（已完成）

- 保留原契约：`evidence_refs`（source_id/snapshot_id/record_id/match_type/score）。
- 新增治理兼容契约：`evidence.items`。
  - 每个 item 包含 `source=trust_data_hub`、`schema_version`、`source_id`、`snapshot_id`、`record_id` 等。
- 输入字段兼容：
  - `road` 支持 `road|street`
  - `poi` 支持 `poi|detail`
- 响应中新增 `input_mapping`，显式披露映射规则，降低联调歧义。

## 3) 验证结果（可验证产出）

- 已执行：
  - `/Users/huda/Code/.venv/bin/python -m pytest services/trust_data_hub/tests/test_trust_data_hub_api.py -q`
- 结果：`12 passed in 0.57s`
- 新增/增强验证点：
  - replay 结果包含 `replay_id`。
  - replay 持久化调用触发（metadb mock）。
  - `street/detail` 输入映射到 `road/poi` 并可回放。
  - `evidence.items` 输出结构与地址治理消费格式兼容。
  - replay-runs 查询接口返回已写入记录。

## 状态回写

- dispatch_batch_id: `dispatch-address-line-closure-004`
- workpackage_id: `wp-trust-hub-replay-persistence-v0.2.0`
- status: `in_progress`
- progress: `86%`
- release_decision: `GO_CANDIDATE`（待真实 Postgres 环境联调完成后最终确认）
