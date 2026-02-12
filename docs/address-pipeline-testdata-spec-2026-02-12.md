# 地址流水线测试数据说明（2026-02-12）

## 1. 文件位置

- `/Users/01411043/code/spatial-intelligence-data-factory/testdata/fixtures/address-pipeline-case-matrix-2026-02-12.json`

## 2. 覆盖范围

1. 有效地址（`raw` / `address` 双字段）
2. 不同层级地址（基础层级、带市级前缀、别名区名）
3. 边界地址（空格、无“号”、道路后缀缺失）
4. 错误地址（缺区、缺路、缺号、噪声字符、跨城市）
5. 与现有场景兼容数据（quick_test 风格、relationship_extraction 风格）

## 3. 使用建议

1. 先对 `expected.cleaning_pass=true` 的样例做回归，确认清洗与图谱门禁都通过。
2. 对 `expected.cleaning_pass=false` 的样例确认返回 `CLEANING_INVALID_OUTPUT`。
3. 将该矩阵接入集成测试，作为 P0 回归基线。

## 4. 注意

1. 当前清洗规则暂不支持“单元/室/楼座”等高阶层级，相关用例在矩阵中标记为预期失败。
2. 后续若扩展规则，需要同步更新矩阵中的 `expected`。
