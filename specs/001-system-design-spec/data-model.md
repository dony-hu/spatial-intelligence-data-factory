# Data Model: 多地交付数据工厂系统规格

## 1. BusinessFoundation（业务基座）
- 字段
- `foundation_id`: 基座标识
- `name`: 基座名称
- `scope_statement`: 范围说明
- `owner_role`: 责任角色
- 关系
- 一个 BusinessFoundation 包含多个 CapabilityDomain

## 2. CapabilityDomain（能力域）
- 字段
- `domain_id`: 能力域标识
- `foundation_id`: 归属基座
- `name`: 能力域名称
- `ownership_type`: `platform` 或 `custom`
- `maturity_level`: 成熟度等级
- 关系
- 一个 CapabilityDomain 可被多个 RepositoryUnit 引用

## 3. RepositoryUnit（仓库单元）
- 字段
- `repo_id`: 仓库标识
- `repo_name`: 仓库名称
- `repo_type`: `core` 或 `regional`
- `region`: 区域标签
- `maintainer_roles`: 维护角色集合
- 关系
- RepositoryUnit 包含多个 DeliveryPackage

## 4. ReviewGate（评审门）
- 字段
- `gate_id`: 评审门标识
- `gate_type`: `business`/`technical`/`compliance`/`release`
- `required_roles`: 必需审批角色
- `entry_criteria`: 进入条件
- `pass_criteria`: 通过条件
- `decision_record_id`: 决策记录引用
- 状态
- `pending` -> `approved`/`rejected` -> `reopened`（可选）

## 5. DeliveryPackage（交付包）
- 字段
- `package_id`: 交付包标识
- `domain_id`: 关联能力域
- `repo_id`: 所属仓库
- `milestone`: 里程碑标识
- `artifact_set`: 产物集合
- `quality_status`: 质量状态
- 关系
- DeliveryPackage 在发布前必须通过所需 ReviewGate

## 6. HumanLoopTask（人机协同任务）
- 字段
- `task_id`: 任务标识
- `automation_scope`: 自动执行范围
- `approval_scope`: 人工审批范围
- `assignee_role`: 审批责任角色
- `audit_trail_id`: 审计记录引用
- 状态
- `generated` -> `submitted` -> `approved`/`rejected` -> `executed`
