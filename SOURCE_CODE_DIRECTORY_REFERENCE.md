# 源代码目录说明（文件夹粒度）

- 生成时间：2026-03-03 11:49:25
- 粒度：目录级（不再逐文件描述）
- 数据来源：`git ls-files -z`（仅统计 Git 跟踪内容）
- 一级目录数：33
- 二级目录数：75

## 一级目录用途

| 目录 | 用途说明 |
|---|---|
| `.chat` | 对话/协作规则配置目录，约束会话行为与任务执行边界。 |
| `.codex` | Codex 提示词与本地工作流配置目录。 |
| `.github` | 代码托管与 CI/CD 配置目录，承载 workflow 与协作规则。 |
| `.opencode` | OpenCode 代理角色与执行配置目录。 |
| `.specify` | Spec Kit 规范驱动开发资产目录（模板、脚本、记忆）。 |
| `.trae` | TRAE 规范、研究与技能资产目录。 |
| `_bmad-output` | BMAD 运行输出目录（规划、实现、汇总产物）。 |
| `archive` | 历史归档目录（旧方案/旧文档/历史证据）。 |
| `bmad` | 项目一级目录，承载对应业务域资产。 |
| `config` | 运行配置目录（数据源、服务参数、环境模板）。 |
| `contracts` | 通用契约域目录（非 workpackage_schema 的其他契约资产）。 |
| `coordination` | 跨角色协同目录（派单、状态同步、执行闭环）。 |
| `data` | 内置数据与示例数据目录。 |
| `database` | 数据库初始化与结构定义目录。 |
| `docs` | 项目文档主目录（PRD/架构/故事/验收/测试）。 |
| `infra` | 基础设施目录（部署、环境、IaC 相关资产）。 |
| `logs` | 运行日志与记录目录。 |
| `migrations` | 数据库迁移目录（Alembic 版本脚本）。 |
| `observability` | 可观测性资产目录（指标、看板、采集约束）。 |
| `output` | 执行产物目录（报告、证据、看板数据、中间产物）。 |
| `packages` | 可复用 Python 包目录（领域能力与组件库）。 |
| `schemas` | 数据结构 schema 目录（跨模块结构定义）。 |
| `scripts` | 自动化脚本目录（启动、校验、验收、治理工具）。 |
| `services` | 服务实现目录（API/Worker/Runtime 等服务边界）。 |
| `settings` | 系统设置与运行配置模板目录。 |
| `specs` | 需求规格目录（按 feature 的 spec/plan/tasks）。 |
| `src` | 应用主代码目录（若存在前端/入口代码）。 |
| `templates` | 模板目录（文档/配置/产物模板）。 |
| `testdata` | 测试数据目录（夹具、样例、治理数据）。 |
| `tests` | 自动化测试目录（单元/集成/E2E）。 |
| `tools` | 开发工具目录（CLI、辅助工具、运维工具）。 |
| `web` | 前端目录（页面、静态资源、看板展示）。 |
| `workpackages` | 工作包发布目录（bundles 可执行包与相关资源）。 |

## 二级目录用途

| 目录 | 用途说明 | 代表内容（示例） |
|---|---|---|
| `.chat/rules` | 子模块目录，主要承载：文档说明。 | `.chat/rules/.gitkeep`<br>`.chat/rules/agent_skills.md`<br>`.chat/rules/governance.md` |
| `.codex/prompts` | 子模块目录，主要承载：文档说明。 | `.codex/prompts/speckit.analyze.md`<br>`.codex/prompts/speckit.checklist.md`<br>`.codex/prompts/speckit.clarify.md` |
| `.github/agents` | 子模块目录，主要承载：流程自动化、文档说明。 | `.github/agents/exp.agent.md` |
| `.github/skills` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `.github/workflows` | 子模块目录，主要承载：流程自动化、测试保障。 | `.github/workflows/nightly-quality-gate.yml`<br>`.github/workflows/p0-workpackage.yml`<br>`.github/workflows/smoke-tests.yml` |
| `.opencode/agents` | 子模块目录，主要承载：文档说明。 | `.opencode/agents/factory.md` |
| `.specify/memory` | 子模块目录，主要承载：流程自动化、文档说明。 | `.specify/memory/constitution.md` |
| `.specify/scripts` | 脚本目录，提供模块内自动化与执行入口。 | - |
| `.specify/templates` | 子模块目录，主要承载：流程自动化、文档说明。 | `.specify/templates/agent-file-template.md`<br>`.specify/templates/checklist-template.md`<br>`.specify/templates/constitution-template.md` |
| `.trae/documents` | 子模块目录，主要承载：文档说明。 | `.trae/documents/architecture-alignment-spatial-intelligence-data-factory-2026-02-11.md`<br>`.trae/documents/architecture-design-data-cleaning-pipeline-v2.md`<br>`.trae/documents/architecture-enhancement-v2-2026-02-17.md` |
| `.trae/skills` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `.trae/specs` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `_bmad-output/implementation-artifacts` | 子模块目录，主要承载：文档说明。 | `_bmad-output/implementation-artifacts/1-1-cli-agent-llm-confirmation.md`<br>`_bmad-output/implementation-artifacts/1-2-dryrun-flow-no-fallback.md`<br>`_bmad-output/implementation-artifacts/1-3-workpackage-publish-runtime.md` |
| `archive/docs` | 子模块目录，主要承载：文档说明。 | `archive/docs/STORY-005-factory-panel.md`<br>`archive/docs/STORY-alignment-check-2026-02-14.md`<br>`archive/docs/STORY-runtime-scripts.md` |
| `archive/specs` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `coordination/dispatch` | 任务派发目录，记录跨角色派单与推进节奏。 | `coordination/dispatch/iteration-001-r2.md`<br>`coordination/dispatch/iteration-001.md`<br>`coordination/dispatch/iteration-002-core-engine-p0-split.md` |
| `coordination/status` | 状态同步目录，记录各角色/工作线状态与风险。 | `coordination/status/address-line-observability-demo-path-2026-02-15.md`<br>`coordination/status/address-line-observability-rollout-2026-02-15.md`<br>`coordination/status/engineering-supervisor.md` |
| `database/postgres` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `docs/acceptance` | 验收文档目录，记录功能/链路验收结论与证据。 | `docs/epics/runtime-observability-v2/acceptance/s2-14-acceptance.json`<br>`docs/epics/runtime-observability-v2/acceptance/s2-14-acceptance.md` |
| `docs/architecture` | 架构设计目录，定义系统分层、模块边界与技术约束；当前引用入口以架构真相源清单为准。 | `docs/02_总体架构/架构索引.md`<br>`docs/02_总体架构/系统总览.md`<br>`docs/02_总体架构/模块边界.md`<br>`docs/02_总体架构/依赖关系.md` |
| `docs/stories` | Story 目录，沉淀可执行故事卡、验收标准与上下文。 | `docs/epics/address-governance-mvp/stories/MVP-A1-CLI-Agent-LLM-对话确认治理需求.md`<br>`docs/epics/address-governance-mvp/stories/MVP-A2-地址治理流程试运行.md`<br>`docs/epics/address-governance-mvp/stories/MVP-A3-工作包发布到数据治理Runtime.md` |
| `docs/testing` | 测试设计目录，沉淀测试策略、用例设计与测试目录索引。 | `docs/09_测试与验收/测试用例目录.md`<br>`docs/09_测试与验收/全链路测试设计.md` |
| `infra/ansible` | 子模块目录，主要承载：文档说明。 | `infra/ansible/README.md`<br>`infra/ansible/ansible.cfg`<br>`infra/ansible/inventory.example.ini` |
| `infra/terraform` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `logs/daily` | 子模块目录，主要承载：文档说明。 | `logs/daily/2026-02-09.md`<br>`logs/daily/2026-02-10.md`<br>`logs/daily/2026-02-11.md` |
| `logs/members` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `logs/summary` | 子模块目录，主要承载：文档说明。 | `logs/summary/2026-W06-weekly-report.md`<br>`logs/summary/weekly-2026-W07.md` |
| `migrations/versions` | 子模块目录，主要承载：契约/结构定义。 | `migrations/versions/20260214_0001_init_addr_governance.py`<br>`migrations/versions/20260215_0002_change_request_and_audit_event.py`<br>`migrations/versions/20260227_0003_unified_schema_alignment.py` |
| `observability/l1` | 子模块目录，主要承载：可观测与看板、文档说明。 | `observability/l1/project_observability_spec.md` |
| `observability/l2` | 子模块目录，主要承载：可观测与看板、文档说明。 | `observability/l2/factory_observability_spec.md` |
| `observability/l3` | 子模块目录，主要承载：可观测与看板、文档说明。 | `observability/l3/line_observability_spec.md` |
| `output/agent_demo` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `output/dashboard` | 子模块目录，主要承载：测试保障、可观测与看板、文档说明。 | `output/dashboard/ITERATION_005_CHANGELOG.md`<br>`output/dashboard/ITERATION_005_DELIVERY_REPORT.md`<br>`output/dashboard/ITERATION_005_SELFTEST_RECORD.md` |
| `output/e2e_dual_real` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `output/lab_mode` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `output/lab_mode/cn1000_expected_from_fengtu_r20_sample20.json`<br>`output/lab_mode/cn1000_expected_from_fengtu_sample3.json`<br>`output/lab_mode/cn1300_module_coverage_20260215_013630.json` |
| `output/line_runs` | 子模块目录，主要承载：测试保障、文档说明。 | `output/line_runs/quick_test_run_2026-02-14.md` |
| `output/observability` | 子模块目录，主要承载：可观测与看板。 | `output/observability/address_line_observability_20260215_195812.png`<br>`output/observability/address_line_observability_demo_20260215_201023.png`<br>`output/observability/address_line_sample_trace_20260215_201023.json` |
| `output/process_expert_bootstrap` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `output/process_expert_bootstrap/bootstrap_debug_20260214_163631.log` |
| `output/test-reports` | 子模块目录，主要承载：测试保障。 | `output/test-reports/acceptance-profiles-20260227-160944.log`<br>`output/test-reports/acceptance-real-llm-gate-20260227-161000.log`<br>`output/test-reports/full_pytest_junit.xml` |
| `output/toolpacks` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `output/toolpacks/address_toolpack.tc06.20260215.json`<br>`output/toolpacks/factory_default_shanghai.json` |
| `output/workpackages` | 子模块目录，主要承载：流程自动化、文档说明。 | `output/workpackages/ARCHITECTURE_TECHNICAL_AUDIT_DISPATCH_006.md`<br>`output/workpackages/dispatch-address-line-closure-001.status.json`<br>`output/workpackages/dispatch-address-line-closure-002-gate-decision.md` |
| `packages/address_core` | 地址治理核心能力目录，承载标准化、解析、匹配等核心逻辑。 | `packages/address_core/dedup.py`<br>`packages/address_core/match.py`<br>`packages/address_core/normalize.py` |
| `packages/agent_runtime` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `packages/agent_runtime/runtime_selector.py` |
| `packages/factory_agent` | 工厂 Agent 目录，负责需求对话、工作包生成与发布编排。 | `packages/factory_agent/__init__.py`<br>`packages/factory_agent/agent.py`<br>`packages/factory_agent/dryrun_workflow.py` |
| `packages/factory_cli` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `packages/factory_cli/__init__.py`<br>`packages/factory_cli/session.py` |
| `packages/governance_runtime` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `packages/governance_runtime/__init__.py` |
| `packages/trust_hub` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `packages/trust_hub/__init__.py` |
| `schemas/agent` | 子模块目录，主要承载：契约/结构定义。 | `schemas/agent/ApprovalPack.json`<br>`schemas/agent/ChangeSet.json`<br>`schemas/agent/EvalReport.json` |
| `scripts/cloud` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `scripts/cloud/bootstrap_k8s_env.sh`<br>`scripts/cloud/install_local_prereqs.sh`<br>`scripts/cloud/provision_volcengine_k8s.sh` |
| `scripts/codex` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `scripts/codex/bootstrap_multicodex.sh`<br>`scripts/codex/show_multicodex_status.sh` |
| `scripts/testdata` | 子模块目录，主要承载：测试保障。 | `scripts/testdata/catalog_tool.py`<br>`scripts/testdata/pull.sh`<br>`scripts/testdata/testdata.sh` |
| `services/governance_api` | 治理 API 服务目录，负责对外接口与业务编排入口。 | `services/governance_api/README.md` |
| `services/governance_worker` | 治理 Worker 服务目录，负责异步任务执行与后台处理。 | - |
| `services/trust_data_hub` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `services/trust_data_hub/Dockerfile`<br>`services/trust_data_hub/docker-compose.yml` |
| `src/agents` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `src/agents/__init__.py`<br>`src/agents/evaluator_adapter.py`<br>`src/agents/executor_adapter.py` |
| `src/common` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `src/common/__init__.py`<br>`src/common/env_bootstrap.py` |
| `src/control_plane` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `src/control_plane/services.py` |
| `src/evaluation` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `src/evaluation/__init__.py`<br>`src/evaluation/gates.py` |
| `src/runtime` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `src/runtime/__init__.py`<br>`src/runtime/errors.py`<br>`src/runtime/evidence_store.py` |
| `src/tools` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `src/tools/__init__.py`<br>`src/tools/airflow_tool.py`<br>`src/tools/ddl_tool.py` |
| `testdata/catalog` | 子模块目录，主要承载：测试保障。 | `testdata/catalog/catalog.yaml` |
| `testdata/contracts` | 子模块目录，主要承载：契约/结构定义、测试保障。 | `testdata/contracts/address_toolpack_shanghai_offline.json`<br>`testdata/contracts/poi.schema.json` |
| `testdata/fixtures` | 子模块目录，主要承载：测试保障。 | `testdata/fixtures/address-graph-cases-1000-2026-02-12.json`<br>`testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json`<br>`testdata/fixtures/address-pipeline-case-matrix-2026-02-12.json` |
| `tests/e2e` | 子模块目录，主要承载：测试保障。 | `tests/e2e/test_address_governance_full_cycle.py` |
| `tests/utils` | 子模块目录，主要承载：测试保障。 | `tests/utils/data_generator.py` |
| `tests/web_e2e` | 子模块目录，主要承载：测试保障、文档说明。 | `tests/web_e2e/README.md`<br>`tests/web_e2e/conftest.py`<br>`tests/web_e2e/test_lab_replay_ui.py` |
| `tools/agent_framework` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `tools/agent_framework/__init__.py`<br>`tools/agent_framework/error_handler.py`<br>`tools/agent_framework/request_response.py` |
| `tools/external_apis` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `tools/external_apis/__init__.py`<br>`tools/external_apis/map_service.py`<br>`tools/external_apis/review_platform.py` |
| `tools/factory_roles` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `tools/factory_roles/__init__.py`<br>`tools/factory_roles/director_service.py`<br>`tools/factory_roles/process_expert_service.py` |
| `tools/generated_tools` | 子模块目录，用于组织当前业务域的实现与配套资产。 | - |
| `tools/process_compiler` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `tools/process_compiler/__init__.py`<br>`tools/process_compiler/compiler.py`<br>`tools/process_compiler/metadata_extractor.py` |
| `tools/process_tools` | 子模块目录，用于组织当前业务域的实现与配套资产。 | `tools/process_tools/__init__.py`<br>`tools/process_tools/create_process_tool.py`<br>`tools/process_tools/create_version_tool.py` |
| `web/dashboard` | 子模块目录，主要承载：可观测与看板。 | `web/dashboard/app.js`<br>`web/dashboard/factory-agent-governance-prototype-v2.html`<br>`web/dashboard/index.html` |
| `workpackages/bundles` | 工作包可执行包目录，每个子目录对应一个可发布运行包。 | - |
| `workpackages/skills` | 子模块目录，主要承载：测试保障、文档说明。 | `workpackages/skills/normalize_address.md`<br>`workpackages/skills/test_skill_e2e.md` |

## 使用说明

1. 本文档用于“目录职责导航”，不替代详细架构设计文档。
2. 若目录职责与实际实现不一致，以对应目录下 README/架构文档为准并应及时修订。
