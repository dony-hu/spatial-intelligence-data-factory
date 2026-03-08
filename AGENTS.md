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

## 文档结构规则（强制）

1. 正式文档文件名不得使用日期后缀；后续更新直接修改 canonical 文件，由 Git 保留历史。
2. 当前正式文档采用“两层结构”：
   - 阅读型正式文档：按编号目录管理，优先使用
     - `docs/01_产品与业务/`
     - `docs/02_总体架构/`
     - `docs/03_数据处理工艺/`
     - `docs/04_系统组件设计/`
     - `docs/05_数据模型设计/`
     - `docs/06_前端与交互设计/`
     - `docs/07_系统运行与运维/`
     - `docs/08_AI能力设计/`
     - `docs/09_测试与验收/`
     - `docs/10_研发与工程规范/`
     - `docs/11_附录/`
   - 例外保留目录：
     - `docs/99_研发过程管理/`
       - 作为唯一过程管理主目录，承接项目级流程文件、研发主题文件与过程归档
3. 所有项目管理和研发过程管理相关文档必须收敛到 `docs/99_研发过程管理/`，不得继续散落在 `docs/` 根目录或并列目录。
4. `docs/99_研发过程管理/99_归档/截止2026-03-05/` 用于存放 `2026-03-05` 及之前的历史过程文档；归档文档不得再当作当前实施基线。
5. `docs/04_系统组件设计/` 内的正式组件文档默认继续按子分组维护：
   - `01_工厂Agent编排/`
   - `02_工作包协议/`
   - `03_Runtime执行/`
   - `04_数据与人工介入/`
   - `05_AI支撑/`
6. 每个研发主题目录至少包含：
   - `主题说明.md`
   - `故事/`
7. 按需补充以下研发主题文档：
   - `产品说明.md`
   - `设计说明.md`
   - `交互设计.md`
   - `验收/`
   - `测试/`
   - `评审记录.md`
   - `复盘记录.md`
   - `冲刺计划.md`
8. 运行态 UX、acceptance、阶段性 PRD/设计等文档，默认应融合为研发主题目录下的正式文件，而不是持续新增 dated 散件。
9. 被替代的 dated 正式文档、一次性评审文档、阶段性过程文档，必须迁入 `archive/docs/` 或 `docs/99_研发过程管理/99_归档/` 对应分区。
10. 旧目录结构 `docs/product/`、`docs/architecture/`、`docs/testing/`、`docs/project-management/` 及已合并的 `docs/12_项目管理/` 已退役；不得再向这些目录新增正式文档。
11. `docs/00_阅读指南.md` 是文档总入口；`docs/02_总体架构/架构索引.md` 是架构真相源入口；新增文档必须遵循这两个入口的分层规则。
12. 禁止在 `docs/` 根目录新增 dated 正式文档、阶段性 UX、阶段性 acceptance、阶段性 sprint/review 文档。
13. 正式文档中的 Mermaid 流程图默认使用纵排：优先 `flowchart TD`；除非用户明确要求或图形语义确实只能横向表达，否则不得使用 `flowchart LR`。
14. 任何后续 AI Coding / Codex / BMAD / SpecKit 任务，在创建、迁移、归档或更新文档前，必须先读取 `docs/99_研发过程管理/文档分层索引.yaml`，按其中 `ai_coding_enforcement` 完成任务分层、落点选择和回填判断。
15. 若 `AGENTS.md` 与其他文档的落点规则冲突，以 `AGENTS.md` 为最高优先级；若无显式冲突，则以 `docs/99_研发过程管理/文档分层索引.yaml` 作为机器可读的默认裁决源。
16. 涉及代码改动时，除遵守测试优先外，还必须判断本次变更是否影响 Ring1 正式知识；若影响，需同步更新对应正式文档，而不能只更新过程主题文档。

## 开发流程规则（强制）

1. 对任何代码改动需求，默认先补充或更新测试用例，再进行功能开发与代码修改。
2. 测试优先顺序：先失败用例（覆盖预期行为/回归点）→ 再实现修复 → 最后运行测试验证。
3. 仅在用户明确说明“跳过用例/紧急修复”时可例外；例外需在回复中注明原因与风险。
4. 若需求无法直接编写自动化用例，需先提供最小可复现脚本或验收检查清单，再开始开发。

## 多Agent与多Worktree并行开发规则（强制）

1. 若进入并行开发模式，必须先读取 `docs/10_研发与工程规范/多Agent与多Worktree并行开发规范.md`。
2. `main` 是唯一集成主干；并行开发分支统一使用 `codex/` 前缀。
3. 一条并行工作流必须同时绑定：一个 Linear Issue / Story、一个 Agent owner、一个 Worktree、一个分支。
4. Worktree 必须放在主仓外部同级目录，不得嵌套到主仓内部。
5. 每个 Worktree 默认独立维护本地虚拟环境、环境变量和运行产物，不得共享本地临时状态。
6. `AGENTS.md`、`docs/00_阅读指南.md`、`docs/02_总体架构/架构索引.md`、`docs/99_研发过程管理/文档分层索引.yaml`、`workpackage_schema/schemas/`、`migrations/versions/` 属于红区对象；并行开发时必须指定唯一 owner 或先做契约 PR。
7. 共享契约必须先合并，再允许下游 Lane 并行实现；不得一边改契约一边让多个 Lane 自由猜测。
8. 合并回 `main` 前，必须同步主干、完成本 Lane 最小测试集，并说明受影响契约与需要回归的下游。
9. `output/`、`docs/.obsidian/workspace.json`、本地缓存和临时数据库文件不得进入正式提交。

## Ring 0 规则（强制）

1. 涉及 LLM 能力验证时，默认必须使用真实外部 LLM 网络调用。
2. 非用户显式指定，不允许使用 mock/stub/fake gateway/本地伪响应替代真实 LLM。
3. 非用户显式指定，不允许使用 workaround（含“workground”）绕过真实链路与验收门禁。
4. 如因外部依赖不可用导致阻塞，必须明确报错与阻塞点，不得伪造成功结果。
5. nanobot 行为收敛必须基于预设配置与 skills 实现；非用户显式批准，不允许修改 nanobot 代码逻辑。
6. opencode 行为收敛必须基于预设配置与 skills/tools 实现；非用户显式批准，不允许修改 opencode 代码逻辑。
7. 上游编排边界强约束：`factory_agent` 负责 `nanobot <-> opencode CLI` 协同以完成工作包开发（生成/修订/dryrun/publish）；不得在上游编排中写入下游运行时专有算法分支。
8. 下游执行边界强约束：`governance_worker` 执行阶段必须仅按 `workpackage_id@version` 装载并执行工作包入口；禁止直接调用与具体治理算法绑定的代码模块。
9. 模块归属强约束：`address_core` 等治理算法实现应封装在工作包 bundle 内；主线 `worker` 不得直接 import/调用 `address_core`。
10. 运行时治理强约束：下游 runtime 框架以“工作包契约执行器”为唯一执行面，不得在 worker 主链路中直接触发 `opencode` 推理调用。


## Active Technologies
- Markdown 规范文档 + Shell 自动化脚本（仓库现状） + GitHub 仓库协作、Spec Kit 工作流、BMAD 方法文档资产 (001-system-design-spec)
- Git 仓库文件系统（核心仓 + 子仓） (001-system-design-spec)

## Recent Changes
- 001-system-design-spec: Added Markdown 规范文档 + Shell 自动化脚本（仓库现状） + GitHub 仓库协作、Spec Kit 工作流、BMAD 方法文档资产

## BMAD 方法仓引用（强制）

1. 本项目默认引用外部 BMAD 方法仓：`/Users/01411043/code/BMAD-METHOD`。
2. 执行 BMAD 工作流命令（如 `/workflow-status`、`/prd`、`/architecture`、`/create-story`、`/dev-story`）前，优先读取方法仓中的 `_bmad/` 与 `docs/` 资产。
3. 项目内配置优先级高于方法仓默认值：`AGENTS.md` > `bmad/config.yaml` > 方法仓模板。
4. 若本机路径不存在，使用环境变量 `BMAD_METHOD_REPO` 指定替代路径；若仍不可达，需在回复中明确“方法仓不可用并采用项目内回退配置”。
5. 禁止在未声明来源的情况下臆造 BMAD 命令、角色定义与模板结构。
