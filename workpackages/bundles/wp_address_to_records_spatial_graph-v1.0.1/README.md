# wp_address_to_records_spatial_graph v1.0.1

将输入 addresses[] 经过地址标准化、真实性校验、地理编码与逆编校验后生成 records[]，并基于距离矩阵构建 spatial_graph。

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