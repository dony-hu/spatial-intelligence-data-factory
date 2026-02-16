# Trust Data Hub Phase1-3 执行计划（2026-02-15）

## 当前状态

已进入 `Phase 1`，并完成可运行能力：

1. 四按钮链路：`Fetch / Validate / Publish / Promote`。
2. namespace 隔离：所有核心 API 与数据读写都要求 `namespace`。
3. Phase 1 扩展：
   1. `source_schedule` 配置接口。
   2. 质量报告查询接口。
   3. active release 查询接口。
   4. validate 回放接口（按 `snapshot_id` 复现证据）。
4. Phase 2 启动器：样板源一键注册（行政区 + OSM Geofabrik China）。
5. Phase 2 第一批已完成：`file/http` fetcher、`file_json/osm_elements_v1` parser profile、publish 可选持久化到 `trust_db`。

## 已交付接口（新增）

1. `PUT /v1/trust/admin/namespaces/{namespace}/sources/{source_id}/schedule`
2. `GET /v1/trust/admin/namespaces/{namespace}/sources/{source_id}/schedule`
3. `GET /v1/trust/admin/namespaces/{namespace}/snapshots/{snapshot_id}/quality`
4. `GET /v1/trust/admin/namespaces/{namespace}/sources/{source_id}/active-release`
5. `POST /v1/trust/validation/replay?namespace=...&snapshot_id=...`
6. `POST /v1/trust/admin/namespaces/{namespace}/bootstrap/samples`

## Phase 2（2-5 周）执行项

1. 接入真实 Fetcher：
   1. 行政区权威源（或可追溯汇编源）下载器。
   2. Geofabrik China extract 下载器。
2. Parser 分离：从 fixture 解析迁移到 profile 驱动解析器。
3. Publisher 落地到 Postgres `trust_db`（替换内存索引）。
4. Validation API 输出结构固化：引入 `schema_version`。
5. 与地址治理 validate stage 做 HTTP 对接联调。

## Phase 3（后续）执行项

1. 多源交叉验证策略（authoritative + open_license + community）。
2. 歧义处理与冲突解释模板。
3. 空间能力扩展（PostGIS + 空间一致性校验）。
4. 授权体系增强：namespace 级访问控制与审计检索。

## 验收标准

1. 任一验证结论可回放到 `source_id + snapshot_id + record_id`。
2. namespace 间查询与证据结果完全隔离。
3. 同一输入地址在 replay 模式下可复现当时证据与信号。
4. Bootstrap 后可在 30 分钟内完成一轮真实源端到端演示。
