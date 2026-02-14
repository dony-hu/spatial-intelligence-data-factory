# 工艺流程文档：工具包生成工艺

- **process_code**: `PROC_TOOLPACK_BOOTSTRAP`
- **requirement**: 请设计工具包生成工艺，要求支持地图API采样、LLM归并、审计回放、迭代改进。
请在工艺中显式体现可信数据源能力编排、证据采集、结论输出与未决风险。
用例总量: 16
优先级分布: {"P0": 5, "P1": 6, "P2": 5}
类别分布: {"mainline_verified_exists": 1, "mainline_verified_not_exists": 1, "mainline_unverifiable_online": 1, "source_conflict_alias": 1, "same_entity_multi_alias": 1, "internet_verification_trainable": 1, "internet_verification_disagreement": 1, "dirty_text_noise": 1, "missing_core_component": 1, "cross_city_mismatch": 1, "write_gate_enforcement": 1, "text_credibility_low": 1, "coord_confidence_low": 1, "new_source_onboarding": 1, "story_truth_completion_graph": 1, "output_contract_completeness": 1}
期望核实状态分布: {"VERIFIED_EXISTS": 5, "VERIFIED_NOT_EXISTS": 1, "UNVERIFIABLE_ONLINE": 7}
可信接口能力索引: {"坐标解析": [{"source_id": "amap_place_text", "interface_id": "default", "interface_name": "高德地图地点检索"}, {"source_id": "baidu_geocoding_v3", "interface_id": "default", "interface_name": "百度地图地理编码"}, {"source_id": "tencent_place_v1", "interface_id": "default", "interface_name": "腾讯位置服务地点搜索"}, {"source_id": "tianditu_geocoder", "interface_id": "default", "interface_name": "天地图地理编码"}], "位置检索": [{"source_id": "amap_place_text", "interface_id": "default", "interface_name": "高德地图地点检索"}, {"source_id": "baidu_geocoding_v3", "interface_id": "default", "interface_name": "百度地图地理编码"}, {"source_id": "tencent_place_v1", "interface_id": "default", "interface_name": "腾讯位置服务地点搜索"}, {"source_id": "tianditu_geocoder", "interface_id": "default", "interface_name": "天地图地理编码"}], "地址完备度评估": [{"source_id": "fengtu", "interface_id": "address_level_judge", "interface_name": "地址级别判断"}], "冲突检测": [{"source_id": "fengtu", "interface_id": "address_level_judge", "interface_name": "地址级别判断"}], "真实性校验": [{"source_id": "fengtu", "interface_id": "address_real_check", "interface_name": "地址真实性校验"}], "结论判定": [{"source_id": "fengtu", "interface_id": "address_real_check", "interface_name": "地址真实性校验"}], "地址类型识别": [{"source_id": "fengtu", "interface_id": "address_type_identify", "interface_name": "地址类型识别"}], "画像分类": [{"source_id": "fengtu", "interface_id": "address_type_identify", "interface_name": "地址类型识别"}], "五级解析": [{"source_id": "fengtu", "interface_id": "address_resolve_l5", "interface_name": "五级地址解析"}], "行政区划解析": [{"source_id": "fengtu", "interface_id": "address_resolve_l5", "interface_name": "五级地址解析"}], "地址标准化": [{"source_id": "fengtu", "interface_id": "address_standardize", "interface_name": "地址标准化"}], "结构化拆解": [{"source_id": "fengtu", "interface_id": "address_standardize", "interface_name": "地址标准化"}], "AOI提取": [{"source_id": "fengtu", "interface_id": "address_aoi_keyword", "interface_name": "地址AOI聚合"}], "地标聚合": [{"source_id": "fengtu", "interface_id": "address_aoi_keyword", "interface_name": "地址AOI聚合"}], "地址核实": [{"source_id": "gov_open_data_address", "interface_id": "default", "interface_name": "政府开放数据地址接口"}]}
工艺输出必须包含: 证据清单、结论段、未决风险段。
- **goal**: 
- **auto_execute**: True
- **max_duration_sec**: 7200
- **quality_threshold**: 0.85

## 步骤

1. 地图API采样
2. LLM归并别名
3. 工具包脚本生成
4. 质量审计回放

## 配置信息

| 配置项 | 值 |
| ---- | ---- |
| 执行优先级 | normal |
| 最大执行时长 | 7200s |
| 质量阈值 | 0.85 |