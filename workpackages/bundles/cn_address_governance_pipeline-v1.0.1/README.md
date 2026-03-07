# cn_address_governance_pipeline v1.0.1

对输入addresses[]执行地址标准化、区划补齐、地理编码、POI真实性校验与实体对齐，产出records[]与spatial_graph；工作包标识为 wp-address-governance-cn@1.0.1。

## 数据源
- fengtu

## 执行方式
```bash
bash entrypoint.sh
```

或
```bash
python entrypoint.py
```