---
name: trusted_map_api_catalog_sf_v1
version: v1.0.0
owner: trust-hub
---

# 已注册可信地图 API 目录（顺丰地图）

来源：`config/trusted_data_sources.json`（`source_id=fengtu`）

## 可用接口（优先用于地址治理）
1. `address_standardize`：地址标准化（POST）
2. `address_real_check`：地址真实性校验（GET）
3. `address_resolve_l5`：五级地址解析（POST）
4. `address_type_identify`：地址类型识别（GET）
5. `geocode`：地理编码（GET）
6. `reverse_geocode`：逆地理编码（GET）
7. `address_level_judge`：地址级别判断（GET）
8. `address_search_service`：地址搜索服务（GET）
9. `address_aoi_keyword`：地址AOI聚合（POST）

## 使用约束
1. 仅允许使用上述已注册接口进行治理方案设计与执行映射。
2. 缺失能力必须走 `missing_apis` 明确声明，不允许隐式 fallback。
3. 涉及 key 的接口，必须明确 `api_key_env` 与用户协助项。
