# Story：TEST-E2E-S5 血缘回放与数据湖产物全链E2E补齐

## 状态

待开始

## 目标

补齐一条从输入来源、工作包版本、执行实例、证据产物到结果对象的完整 E2E 血缘链。

## 验收标准

1. 至少一条用例一次性覆盖 `source_snapshot_id -> input_binding_ref -> publish_id -> task_id -> trace_id -> evidence_ref -> canonical_record`。
2. 同时覆盖 PG 索引对象和 `output/` 产物层。
3. 可从正向链和逆向链两个方向验证。

## 交付物

1. `docs/09_测试与验收/全链路测试设计.md`
2. `docs/09_测试与验收/E2E用例模板.md`
