# Story 3.9 - 观测权限脱敏与审计合规

Status: done

## 目标

为运行态可观测下钻能力补齐单租户最小 RBAC 与数据脱敏，满足最小合规要求。

## Tasks

- [x] T1: 先补失败用例（TDD）
- [x] T1.1: 新增 RBAC 鉴权失败用例
- [x] T1.2: 新增字段脱敏一致性失败用例
- [x] T1.3: 新增审计事件完整性失败用例
- [x] T2: 实现权限、脱敏与审计闭环
- [x] T2.1: 实现 viewer/oncall/admin 角色能力边界
- [x] T2.2: 实现任务详情与导出的脱敏策略
- [x] T2.3: 敏感操作审计可回查
- [x] T3: 回归与验证
- [x] T3.1: 运行合规 RBAC 契约回归
- [x] T3.2: 运行运行态可观测回归矩阵

## 验收标准

1. 未授权访问被显式拒绝。
2. 脱敏规则对页面/API 一致生效。
3. 敏感操作有审计事件可回查。
4. 导出能力遵守角色限制。
5. 鉴权失败返回明确权限错误。
6. 不引入多租户 RBAC 设计。

## Dev Agent Record

### Completion Notes

- 已通过 `test_runtime_compliance_rbac.py` 与 `test_runtime_workpackage_observability_rbac.py`，验证 RBAC、脱敏与审计闭环可用。

## File List

- services/governance_api/app/services/governance_service.py
- services/governance_api/app/routers/observability.py
- services/governance_api/tests/test_runtime_compliance_rbac.py
- services/governance_api/tests/test_runtime_workpackage_observability_rbac.py
- _bmad-output/implementation-artifacts/3-9-observability-permission-masking-and-audit-compliance.md

## Change Log

- 2026-03-02: 执行 `W-DEV` 推进 Story 3.9 至 `done`，补齐实现工件与验证记录。
