# TC-03 工具/引擎版本基线与兼容矩阵

更新时间：2026-02-14

## 1) 版本基线（当前仓内已落地）

| 组件 | 字段 | 当前值 | 来源 |
|---|---|---|---|
| WorkPackage | `workpackage_version` | `1.0.1` | `workpackages/wp-address-topology-v1.0.1.json` |
| 工艺版本 | `process_version` | `process-v1.0.1` | `workpackages/wp-address-topology-v1.0.1.json` |
| 工具包版本 | `tool_bundle_version` | `tools-v1.0.1` | `workpackages/wp-address-topology-v1.0.1.json` |
| 执行引擎版本 | `engine_version` | `engine-v1.0.1` | `workpackages/wp-address-topology-v1.0.1.json` |
| Terraform CLI 约束 | `terraform_required_version` | `>= 1.5.0` | `infra/terraform/volcengine/versions.tf` |
| Terraform 安装脚本版本 | `terraform_install_version` | `1.7.5` | `scripts/cloud/install_local_prereqs.sh` |
| Terraform Provider | `volcengine_provider_version` | `>= 0.0.159` | `infra/terraform/volcengine/versions.tf` |
| K8s 版本 | `kubernetes_version` | `1.30` | `infra/ansible/group_vars/all.yml` |
| 测试数据目录版本 | `catalog_version` | `2026.02.11` | `testdata/catalog.yaml` |

## 2) 兼容字段输出规范（最小可用）

- `engine_version`：执行引擎版本（示例：`engine-v1.0.1`）
- `toolchain_version`：工具链/工具包版本（示例：`tools-v1.0.1`）
- `compat_matrix`：兼容矩阵对象，至少包含：
  - `process_version`
  - `workpackage_version`
  - `engine_version`
  - `toolchain_version`
  - `verified_at`
  - `verification_artifact`

## 3) 兼容矩阵（本轮）

```json
{
  "process_version": "process-v1.0.1",
  "workpackage_version": "1.0.1",
  "engine_version": "engine-v1.0.1",
  "toolchain_version": "tools-v1.0.1",
  "verified_at": "2026-02-14",
  "verification_artifact": "output/line_runs/quick_test_run_2026-02-14.md"
}
```

## 4) 已识别风险

- 当前 `execution_result.json` 尚未统一输出 `engine_version/toolchain_version/compat_matrix` 字段，需在下一轮补齐执行结果侧字段落地。
