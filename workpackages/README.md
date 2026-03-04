# WorkPackage 目录

本目录存放工厂下发给产线的工作包版本。

## 原则

- 工作包由工厂系统生成，产线系统只消费。
- 工作包必须满足 `workpackage_schema/registry.json` 指向的当前版本 schema（当前为 `v1`）。
- 每次发布必须包含回滚信息。

## 协议约束

- 旧协议文件已清理，新增工作包不得回退到非版本化契约。
- 读取 schema 时必须通过 `workpackage_schema/registry.json` 解析版本，禁止硬编码路径。

## 命名建议

- `wp-<line>-v<major>.<minor>.<patch>.json`
- 示例：`wp-address-topology-v1.0.0.json`
