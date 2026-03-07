# address_governance_records_spatial v1.0.0

对输入addresses[]执行地址标准化、五级解析、真实性与类型识别、地理编码一致性校验，产出records[]与spatial_graph，并输出可审计失败码与SLA统计。

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