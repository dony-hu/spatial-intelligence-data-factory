# AGENTS 项目级规则

## 研发管理看板规则

1. 本项目采用 **Linear** 进行研发任务追踪与敏捷协作。
2. 废弃仓库内自研的 `factory_dashboard.py` 及 `logs/daily/*.md` 中的手动看板逻辑。
3. 所有新任务（Issue）、Bug 修复与功能迭代需在 Linear 中创建，并与 GitHub PR 关联。
4. 业务数据看板（如产线运行状态、地址治理覆盖率）仍通过项目内的 `output/dashboard/` 生成并展示。

## 文档语言（强制）

1. 本仓库内所有新建或更新的项目文档默认使用中文。
2. 所有 skills 在生成文档时必须应用本规则。
3. 仅当用户需求或外部交付明确要求非中文时，才可使用其他语言，并在文档中注明原因与适用范围。

## 开发流程规则（强制）

1. 对任何代码改动需求，默认先补充或更新测试用例，再进行功能开发与代码修改。
2. 测试优先顺序：先失败用例（覆盖预期行为/回归点）→ 再实现修复 → 最后运行测试验证。
3. 仅在用户明确说明“跳过用例/紧急修复”时可例外；例外需在回复中注明原因与风险。
4. 若需求无法直接编写自动化用例，需先提供最小可复现脚本或验收检查清单，再开始开发。


## Active Technologies
- Markdown 规范文档 + Shell 自动化脚本（仓库现状） + GitHub 仓库协作、Spec Kit 工作流、BMAD 方法文档资产 (001-system-design-spec)
- Git 仓库文件系统（核心仓 + 子仓） (001-system-design-spec)

## Recent Changes
- 001-system-design-spec: Added Markdown 规范文档 + Shell 自动化脚本（仓库现状） + GitHub 仓库协作、Spec Kit 工作流、BMAD 方法文档资产
