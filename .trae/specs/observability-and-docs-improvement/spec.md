# 可观测性与文档完善 Spec

## Why
- 项目当前可观测性数据更新需手动触发，缺少自动化集成；文档中存在大量硬编码路径，影响新开发者体验。
- 根据高级架构师审视报告，可观测性与文档层是项目短板（75/100 和 70/100），需优先改进。

## What Changes
- **修复 .gitignore**: 补充 `.venv/` 忽略规则
- **看板自动化**: 在 E2E 测试通过后自动运行 `collect_governance_metrics.py` 并更新看板
- **文档规范化**: 批量替换文档中的硬编码绝对路径为相对路径
- **统一配置管理**: 引入 `pydantic-settings` 管理环境配置（可选，根据优先级决定）

## Impact
- **Affected specs**: `system-status-planning`, `real-db-integration-and-dashboard`
- **Affected code**:
  - `.gitignore` (修改)
  - `tests/e2e/test_address_governance_full_cycle.py` (修改，或新增集成脚本)
  - `docs/**/*.md` (批量修改)
  - 新增 `config/settings.py` (可选)

## ADDED Requirements

### Requirement: Gitignore 完整性
**WHEN** 开发者提交代码  
**THEN** `.venv/` 虚拟环境不会被误提交到仓库

### Requirement: 看板自动化更新
**WHEN** E2E 测试 `test_address_governance_full_cycle.py` 执行成功  
**THEN** 自动调用 `scripts/collect_governance_metrics.py` 并更新 `output/dashboard/governance_dashboard.html`

### Requirement: 文档路径规范化
**WHEN** 新开发者阅读项目文档  
**THEN** 所有路径引用为相对路径，可直接在本地环境复现

## MODIFIED Requirements
无

## REMOVED Requirements
无
