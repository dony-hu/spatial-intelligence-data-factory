# 地址工具包工厂生成说明（2026-02-14）

## 目标
- 地址产线运行时保持离线，不连接 LLM/互联网。
- 工厂服务先通过互联网地图 API 采样，再用 LLM 做归并迭代，产出工具包给产线调用。

## 阶段拆分
1. 工厂构建阶段（在线）
   - 输入种子地址集合
   - 调用地图 API 抽取 city/district 观测
   - 可选调用 LLM 归并别名和区划结构
   - 输出工具包 JSON

2. 产线运行阶段（离线）
   - 仅加载工具包
   - 不允许内置地域先验
   - 不允许联网查询

## 新增能力
- 构建器模块：`tools/address_toolpack_builder.py`
- 执行脚本：`scripts/build_address_toolpack.py`
- 模板文件：`testdata/contracts/address_toolpack_shanghai_offline.json`（仅模板，不含地域知识）

## 使用示例
```bash
cd /Users/huda/Code/worktrees/factory-address-verify

/Users/huda/Code/.venv/bin/python scripts/build_address_toolpack.py \
  --seed-file testdata/fixtures/address_samples_seed.json \
  --output-file runtime_store/generated_toolpacks/address_toolpack_generated.json \
  --map-api-url "${MAP_TOOLPACK_API_URL}" \
  --map-api-key "${MAP_TOOLPACK_API_KEY}" \
  --llm-config config/llm_api.json
```

## 产线接入
```bash
export FACTORY_ADDRESS_TOOLPACK_PATH=/Users/huda/Code/worktrees/factory-address-verify/runtime_store/generated_toolpacks/address_toolpack_generated.json
```

未设置该变量时，标准化步骤应返回 `MISSING_TOOLPACK`。
