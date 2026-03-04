# addr_governance_mvp v1.0.0

对输入 addresses[] 执行地址标准化、五级解析、地理编码/逆编码一致性校验、地址真实性校验与类型识别，输出 records[] 与 spatial_graph，用于地址治理与可达性分析。

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