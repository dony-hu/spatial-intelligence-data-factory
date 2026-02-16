# Trust Data Hub v0.1 工作线启动说明

## 1. 本次交付范围

本工作线在仓库内新增了一个可独立运行的 `Trust Data Hub` 子系统骨架，覆盖以下能力：

1. 控制面与执行面接口：`Fetch / Validate / Publish / Promote / Diff`。
2. 元数据管理：`source_registry`、`source_snapshot`、`quality_report`、`diff_report`、`active_release`、`audit_event` 的内存版仓储语义。
3. 服务接口：
   1. `Query API`：行政区、道路、POI 查询。
   2. `Validation API`：输出证据链（含 `source_id` 与 `snapshot_id`）。
4. 单机部署骨架：`trust-api`、`trust-worker`、`trust-scheduler`、`trust-meta-postgres` 的 Compose 文件。
5. PostgreSQL 初始化 DDL：`trust_meta` + `trust_db` 两套 schema。

## 2. 目录与文件

- API 主入口：`/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/app/main.py`
- 核心仓储：`/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/app/repositories/trust_repository.py`
- 路由：
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/app/routers/admin.py`
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/app/routers/ops.py`
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/app/routers/query.py`
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/app/routers/validation.py`
- 部署：
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/docker-compose.yml`
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/Dockerfile`
- 调度与执行占位：
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/ops/worker.py`
  - `/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/ops/scheduler.py`
- 数据库 DDL：`/Users/huda/Code/spatial-intelligence-data-factory/database/trust_meta_schema.sql`
- 测试：`/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/tests/test_trust_data_hub_api.py`

## 3. 快速启动（单机 Docker Compose）

在仓库根目录执行：

```bash
docker compose -f services/trust_data_hub/docker-compose.yml up --build
```

API 默认端口：`8082`。

## 4. 最小验收流程

1. 注册数据源
```bash
NAMESPACE="system.trust"
curl -X PUT "http://localhost:8082/v1/trust/admin/namespaces/${NAMESPACE}/sources/src-admin-001" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"admin sample",
    "category":"admin_division",
    "trust_level":"authoritative",
    "license":"ODbL",
    "entrypoint":"fixture://admin_division",
    "update_frequency":"daily",
    "fetch_method":"download",
    "parser_profile":{"dataset_variant":"admin_v1"},
    "validator_profile":{"max_null_ratio":0.2},
    "enabled":true,
    "allowed_use_notes":"cache allowed",
    "access_mode":"download",
    "robots_tos_flags":{"allow_automation":true,"require_attribution":true}
  }'
```

2. Fetch / Validate / Publish / Promote
```bash
SNAPSHOT_ID=$(curl -s -X POST "http://localhost:8082/v1/trust/ops/namespaces/${NAMESPACE}/sources/src-admin-001/fetch-now" | jq -r .snapshot_id)
curl -X POST "http://localhost:8082/v1/trust/ops/namespaces/${NAMESPACE}/snapshots/${SNAPSHOT_ID}/validate"
curl -X POST "http://localhost:8082/v1/trust/ops/namespaces/${NAMESPACE}/snapshots/${SNAPSHOT_ID}/publish"
curl -X POST "http://localhost:8082/v1/trust/ops/namespaces/${NAMESPACE}/sources/src-admin-001/promote" \
  -H "Content-Type: application/json" \
  -d "{\"snapshot_id\":\"${SNAPSHOT_ID}\",\"activated_by\":\"ops\",\"activation_note\":\"go-live\"}"
```

3. 查询与证据输出
```bash
curl "http://localhost:8082/v1/trust/query/namespaces/${NAMESPACE}/admin-division?name=杭州市"
curl -X POST "http://localhost:8082/v1/trust/validation/evidence?namespace=${NAMESPACE}" \
  -H "Content-Type: application/json" \
  -d '{"province":"浙江省","city":"杭州市","district":"西湖区","road":"文三路","poi":"西溪银泰城"}'
```

## 5. 当前限制（v0.1 起步态）

1. 目前数据获取使用 fixture 数据集模拟（`admin_v1/admin_v2/osm_china_v1`），未接真实下载器。
2. Worker/Scheduler 为可运行骨架，未接真实任务队列。
3. 当前 Trust DB 持久化仍在内存仓储层语义实现，Postgres DDL 已就绪但尚未打通 ORM/DAO。

## 6. 后续建议

1. 将 `TrustRepository` 分层为 `MetaRepository` + `TrustIndexRepository`，并接入 SQLAlchemy。
2. 为 Geofabrik/行政区数据源新增真实 Fetcher + Parser Profile。
3. 在 `Publish` 增加 bulk upsert 与索引刷新策略。
4. 将 `Validation API` 与现有地址治理 `validate stage` 通过 HTTP 契约对接，固定 evidence schema 版本号。
