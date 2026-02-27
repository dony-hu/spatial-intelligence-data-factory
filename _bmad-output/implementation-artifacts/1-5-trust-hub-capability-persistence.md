# Story 1.5 - Trust Hub 能力与样例数据沉淀

Status: done

## 目标

将 Trust Hub 从 API Key 存储扩展到“能力注册 + 样例数据沉淀 + 查询重载”。

## Tasks

- [x] 能力注册非法输入阻塞测试
- [x] 样例数据持久化与重载测试
- [x] Agent `supplement_trust_hub` 接入真实沉淀逻辑
- [x] 对接 trust_meta/trust_db 查询接口验证

## 交付物

- `packages/trust_hub/__init__.py`
- `packages/factory_agent/agent.py`
- `tests/test_trust_hub_persistence_no_fallback.py`
- `tests/test_trust_hub_trustdb_query.py`
