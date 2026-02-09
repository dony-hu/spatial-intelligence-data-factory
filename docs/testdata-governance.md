# 测试数据治理规范

## 范围

本文档定义本仓库中测试数据集的创建、存储、版本管理与使用方式。

## 数据集策略

1. 允许的数据类别：`synthetic`、`masked`。
2. 禁止提交到 Git：生产原始导出数据、未脱敏 PII、大体积快照。
3. 每个数据集都必须在 `testdata/catalog/catalog.yaml` 中登记。

## 命名规范

- 数据集 ID：`<domain>_<scenario>_<level>`（例如：`geo_poi_smoke_p0`）。
- 版本号：`vYYYY.MM.DD.N`。
- 文件名：`<dataset_id>__<version>__<format>.<ext>`。

## 元数据要求

每条清单记录必须包含：

- `id`, `version`, `level`, `purpose`, `owner`, `source`
- `pii` (`none|masked|synthetic`)
- `retention_days`
- `storage` (`type`, `uri`)
- `checksum` (`algo`, `value`)

## 生命周期

1. 在 `catalog.yaml` 中登记数据需求。
2. 生成数据集或执行脱敏处理。
3. 计算校验和（checksum）。
4. 小样本提交到仓库；大数据上传到对象存储。
5. 在 CI 中执行 `scripts/testdata/pull.sh` 与 `scripts/testdata/verify.sh`。
6. 按 `retention_days` 清理过期数据。

## 访问控制

- 对象存储访问必须采用最小权限和短时凭证。
- 必须按环境隔离（`dev`、`test`、`stage`）。
- 原始来源数据仅允许经审批的操作人员直接访问。
