# Workpackage Bundle 目录模板（v1）

```text
{{bundle_name}}/
├── workpackage.json
├── entrypoint.py
├── entrypoint.sh
├── README.md
├── scripts/
│   └── run_pipeline.py
├── skills/
│   └── address_governance_skill.md
├── observability/
│   ├── line_observe.py
│   └── line_metrics.json
├── input/
│   └── sample_addresses_10.csv
└── config/
    └── provider_keys.env.example
```

## 最小可执行要求
- `python3 entrypoint.py` 可直接执行。
- `skills/` 目录必须存在，且 `workpackage.json` 的 `skills[].path` 必须全部可解析到该目录。
- 输出 `output/runtime_output.json`，且包含：
  - `records[]`（每条地址含 normalization/entity_parsing/address_validation）
  - `spatial_graph`（含 nodes/edges/metrics/failed_row_refs/build_status）
