# WorkPackage 目录

本目录存放工厂下发给产线的工作包版本。

## 原则

- 工作包由工厂系统生成，产线系统只消费。
- 工作包必须满足 `contracts/workpackage.schema.json`。
- 每次发布必须包含回滚信息。

## 命名建议

- `wp-<line>-v<major>.<minor>.<patch>.json`
- 示例：`wp-address-topology-v1.0.0.json`
