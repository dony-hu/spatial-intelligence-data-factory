# {{workpackage_name}}（{{workpackage_version}}）

## 工作包目标
- `id`: `{{workpackage_id}}`
- `objective`: {{objective}}
- `schema_version`: `workpackage_schema.v1`

## 文件结构与职责
- `workpackage.json`
  - 协议实例主文件，定义工作包目标、输入输出 schema、API 计划、执行步骤、门禁策略。
- `entrypoint.py`
  - Runtime 直接调用入口（Python）。负责编排主流程脚本与观测脚本。
- `entrypoint.sh`
  - Shell 入口。便于调度器、命令行统一调用。
- `README.md`
  - 当前工作包说明文档（本文件）。
- `scripts/run_pipeline.py`
  - 核心治理逻辑：地址标准化、验真、实体拆分、图谱构建。
- `skills/`
  - 技能目录。`workpackage.json` 中 `skills[]` 字段声明的技能文件必须在此目录可用。
- `observability/line_observe.py`
  - 运行后观测脚本，生成指标与可审计输出。
- `observability/line_metrics.json`
  - 观测指标输出（记录数、图谱节点/边、构建状态）。
- `input/sample_addresses_10.csv`
  - 样例输入数据（10条地址）。
- `config/provider_keys.env.example`
  - 外部 API Key 模版，列出运行所需的 key 环境变量。

## 执行方式
```bash
cd workpackages/bundles/{{bundle_name}}
python3 entrypoint.py
```

## 运行产物
- `output/runtime_output.json`
- `output/records.json`
- `output/spatial_graph.json`
- `output/preprocessed_addresses.csv`
- `observability/line_metrics.json`

## 门禁要求
- 未 `confirm_generate`：禁止 packaged。
- 未 `confirm_publish`：禁止 submitted。

## 备注
- 禁止 mock/fallback 绕过真实链路。
- 外部依赖不可用时，必须输出真实错误与阻塞点。
