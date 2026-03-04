---
title: '工作包 CRUD API 与可视化检索及测试数据构造'
slug: 'workpackage-crud-search-seed-data'
created: '2026-03-03T13:44:21+0800'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.11', 'FastAPI', 'SQLAlchemy+psycopg2', 'PostgreSQL', '原生 HTML/JS 仪表页', 'Pytest', 'Playwright']
files_to_modify: [
  'services/governance_api/app/routers/observability.py',
  'services/governance_api/app/services/governance_service.py',
  'services/governance_api/app/repositories/governance_repository.py',
  'web/dashboard/factory-agent-governance-prototype-v2.html',
  'services/governance_api/tests/test_runtime_workpackage_crud_api_contract.py',
  'services/governance_api/tests/test_runtime_workpackage_seed_data_api.py',
  'tests/web_e2e/test_runtime_observability_workpackage_search_ui.py'
]
code_patterns: ['Router -> Service -> Repository 分层', '路由层统一把 ValueError 映射为 HTTP 400+业务 code', 'repository 同时维护 memory cache + PostgreSQL 落库', 'runtime 页面 data-testid 驱动 E2E', 'PostgreSQL 优先（no-fallback）']
test_patterns: ['先失败后实现(TDD)', 'FastAPI TestClient 合约测试', 'Playwright 纯 Web E2E', '真实链路开关由环境变量控制（如 RUN_REAL_LLM_WEB_E2E）']
---

# Tech-Spec: 工作包 CRUD API 与可视化检索及测试数据构造

**Created:** 2026-03-03T13:44:21+0800

## Overview

### Problem Statement

当前系统在“工作包”维度已有部分查询与发布能力（如运行时 pipeline/events/blueprint 与 ops 下版本查询），但缺少统一、可维护的工作包 CRUD API；前端页面也缺少针对工作包的完整查询/检索入口；同时缺少一组稳定的测试工作包数据用于 API 与 Web E2E 验证。

### Solution

新增一组以工作包为中心的 CRUD API（创建/查询列表/查询详情/更新/删除），在可视化页面增加工作包检索交互（关键词、状态、版本过滤及结果列表），并提供可重复导入的工作包测试数据与自动化测试覆盖。

### Scope

**In Scope:**
- 新增工作包 CRUD API（含请求校验、错误码、DB 持久化、分页/过滤查询）。
- 可视化页面新增工作包检索区域（输入、过滤、列表、选择后联动详情）。
- 构造并落库/导入若干工作包测试数据（至少覆盖 created/submitted/packaged/published/blocked 等状态）。
- API 与 Web E2E 自动化测试补齐，覆盖主路径和关键异常路径。

**Out of Scope:**
- 不改动工作包执行引擎的核心处理逻辑（dryrun/publish 实际执行算法）。
- 不引入新的前端框架重构（保持当前 HTML + JS 页面结构）。
- 不引入 mock/fallback/workground 方案替代真实链路。

## Context for Development

### Codebase Patterns

- 路由层模式：`observability.py` 通过 `Query` 与 payload 做输入约束，服务层异常主要通过 `ValueError -> HTTPException(400)` 转换。
- 服务层模式：`governance_service.py` 提供 `runtime_workpackage_pipeline/events/blueprint/seed` 等聚合能力，优先从 repository 拉取事件并做窗口过滤与中文字段映射。
- 仓储层模式：`governance_repository.py` 对工作包“发布记录”已有 `upsert/get/list/compare`；结构是 `workpackage_id+version` 复合键 + PostgreSQL `ON CONFLICT` upsert，同时保留内存缓存。
- 前端页面模式：`factory-agent-governance-prototype-v2.html` 采用原生 JS `fetch + data-testid`，当前工作包来源是 pipeline 列表与 selector 联动，尚无独立搜索表单。
- 测试模式：后端 API 用 `TestClient`，Web 用 Playwright；已有工作包蓝图/聊天/长链路测试可直接复用断言风格。
- 项目强约束：PostgreSQL 主链路、no-fallback/no-mock。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `services/governance_api/app/routers/observability.py` | 新增 runtime workpackages CRUD/search 路由，并保持错误码风格一致 |
| `services/governance_api/app/services/governance_service.py` | 新增 CRUD/search 业务编排、过滤与排序逻辑 |
| `services/governance_api/app/repositories/governance_repository.py` | 新增工作包实体 CRUD（独立于 publish 记录）与 seed 数据写入/清理能力 |
| `services/governance_api/app/routers/ops.py` | 参考已有 workpackage 版本查询语义，避免接口定义冲突 |
| `web/dashboard/factory-agent-governance-prototype-v2.html` | 增加工作包检索表单、结果列表与详情联动 |
| `services/governance_api/tests/test_runtime_workpackage_blueprint_api_contract.py` | 参考 runtime 工作包接口测试风格 |
| `services/governance_api/tests/test_runtime_agent_chat_api.py` | 参考 runtime 路由回包结构断言风格 |
| `tests/web_e2e/test_runtime_observability_agent_chat_ui.py` | 复用现有页面元素与 E2E 组织方式，新增检索场景测试 |

### Technical Decisions

- CRUD API 路由建议统一在 `/v1/governance/observability/runtime/workpackages` 下，保持 runtime 语义一致。
- 列表接口支持查询参数：`q`（模糊关键词）、`status`、`version`、`limit`、`offset`。
- 列表接口补充排序参数：`sort_by`（默认 `updated_at`）、`sort_order`（`asc/desc`，默认 `desc`）。
- 详情/更新/删除使用路径键：`/workpackages/{workpackage_id}/versions/{version}`。
- 删除采用软删（`deleted_at` 标记），默认列表不返回已删除记录。
- 统一错误返回：参数错误使用 `400 INVALID_PAYLOAD`，资源不存在使用 `404`。
- 数据模型以 `workpackage_id + version` 为逻辑唯一键；更新与删除都需显式传入二者。
- 统一响应结构：`code/message/data/request_id`。
- 页面检索不做前端缓存“真源”，以后端查询结果为准，避免状态漂移。
- 页面新增稳定检索 testid：`workpackage-search-input`、`workpackage-status-filter`、`workpackage-version-filter`、`workpackage-search-button`、`workpackage-search-reset`、`workpackage-search-results`。
- 测试数据策略：新增专用 seed API（或复用现有 seed-workpackage-demo 扩展参数）产出可预测 ID（如 `wp_seed_crud_001`）以提高测试可重复性。

## Implementation Plan

### Tasks

- [ ] Task 1: 定义工作包 CRUD API 数据契约与响应模型
  - File: `services/governance_api/app/models/observability_models.py`
  - Action: 新增 runtime workpackage CRUD 的 request/response Pydantic 模型（create/update/list/detail/delete），统一包含 `code/message/data/request_id`。
  - Notes: `status` 字段允许值与现有 pipeline 状态对齐；列表查询模型包含 `q/status/version/limit/offset/sort_by/sort_order`。

- [ ] Task 2: 新增工作包实体仓储 CRUD 能力（不复用 publish 记录）
  - File: `services/governance_api/app/repositories/governance_repository.py`
  - Action: 新增 `create/get/list/update/soft_delete` 方法，实体键为 `workpackage_id+version`，支持 `deleted_at` 软删与过滤。
  - Notes: DB 路径使用 PostgreSQL SQL + `ON CONFLICT`；同时更新 memory cache 以兼容进程内读取。

- [ ] Task 3: 在服务层编排 CRUD/检索/测试数据灌入能力
  - File: `services/governance_api/app/services/governance_service.py`
  - Action: 新增 `runtime_workpackage_create/list/get/update/delete/seed_crud_demo` 方法，处理参数规范化、排序、分页、错误语义。
  - Notes: 参数错误抛 `ValueError`，路由层统一转 `400 INVALID_PAYLOAD`；保留 no-fallback 行为。

- [ ] Task 4: 暴露 runtime workpackages CRUD 路由
  - File: `services/governance_api/app/routers/observability.py`
  - Action: 新增以下路由：
    - `POST /observability/runtime/workpackages`
    - `GET /observability/runtime/workpackages`
    - `GET /observability/runtime/workpackages/{workpackage_id}/versions/{version}`
    - `PUT /observability/runtime/workpackages/{workpackage_id}/versions/{version}`
    - `DELETE /observability/runtime/workpackages/{workpackage_id}/versions/{version}`
    - `POST /observability/runtime/workpackages/seed-crud-demo`
  - Notes: 保持现有错误映射风格，`ValueError -> 400`，不存在资源返回 `404`。

- [ ] Task 5: 页面新增工作包检索区与结果列表
  - File: `web/dashboard/factory-agent-governance-prototype-v2.html`
  - Action: 增加检索输入与筛选控件（关键词、状态、版本、查询、重置）及结果容器，提供稳定 `data-testid`。
  - Notes: 新增 testid：`workpackage-search-input`、`workpackage-status-filter`、`workpackage-version-filter`、`workpackage-search-button`、`workpackage-search-reset`、`workpackage-search-results`。

- [ ] Task 6: 页面联动逻辑对接新检索 API
  - File: `web/dashboard/factory-agent-governance-prototype-v2.html`
  - Action: 新增 `loadWorkpackageSearchResults()` 并接入点击结果后刷新 selector、events、blueprint 面板；重置行为恢复默认条件。
  - Notes: 保持现有 `loadPipeline` 不受破坏，检索区作为新增能力而非替代。

- [ ] Task 7: 新增 API 合约测试（TDD 先失败）
  - File: `services/governance_api/tests/test_runtime_workpackage_crud_api_contract.py`
  - Action: 覆盖创建、列表检索、详情、更新、删除、删除后不可见、缺参 `400 INVALID_PAYLOAD`、不存在 `404`。
  - Notes: 使用 `TestClient`，请求与响应断言采用现有 runtime API 契约风格。

- [ ] Task 8: 新增测试数据灌入接口测试
  - File: `services/governance_api/tests/test_runtime_workpackage_seed_data_api.py`
  - Action: 验证 seed 返回数量、状态覆盖、版本覆盖、中英文名称覆盖与幂等性。
  - Notes: 采用可预测 ID 前缀（例如 `wp_seed_crud_`）降低测试脆弱性。

- [ ] Task 9: 新增 Web 检索 E2E 用例
  - File: `tests/web_e2e/test_runtime_observability_workpackage_search_ui.py`
  - Action: 覆盖页面搜索、状态过滤、重置、点击结果联动详情面板、无结果提示。
  - Notes: 纯 Web 交互，不走脚本级集成替代。

### Acceptance Criteria

- [ ] AC 1: Given 提供合法 `workpackage_id+version+objective+status` 创建请求，When 调用创建 API，Then 返回 `200` 且 `data` 中回包键与入参一致。
- [ ] AC 2: Given 缺少 `workpackage_id` 或 `version` 的创建请求，When 调用创建 API，Then 返回 `400` 且 `detail.code=INVALID_PAYLOAD`。
- [ ] AC 3: Given 已存在多条工作包记录，When 调用列表 API 并传入 `q/status/version`，Then 结果仅包含匹配项且支持 `limit/offset/sort_by/sort_order`。
- [ ] AC 4: Given 指定 `workpackage_id+version` 存在，When 调用详情 API，Then 返回完整记录（含 `created_at/updated_at/status`）。
- [ ] AC 5: Given 指定 `workpackage_id+version` 不存在，When 调用详情 API，Then 返回 `404`。
- [ ] AC 6: Given 指定 `workpackage_id+version` 存在，When 调用更新 API 修改 `objective/status`，Then 再次查询可见更新值且 `updated_at` 变化。
- [ ] AC 7: Given 指定 `workpackage_id+version` 存在，When 调用删除 API，Then 默认列表查询不可见该记录，详情返回 `404`。
- [ ] AC 8: Given 调用 seed API，When 指定数量 `>=12`，Then 返回记录覆盖 `created/submitted/packaged/published/blocked/deleted` 六类状态。
- [ ] AC 9: Given seed 数据中同一 `workpackage_id` 多版本存在，When 通过版本过滤查询，Then 仅返回对应版本。
- [ ] AC 10: Given 页面已加载并有 seed 数据，When 在 `workpackage-search-input` 输入关键词后点击 `workpackage-search-button`，Then `workpackage-search-results` 显示匹配结果。
- [ ] AC 11: Given 页面已按状态过滤，When 点击 `workpackage-search-reset`，Then 过滤条件清空并恢复默认结果列表。
- [ ] AC 12: Given 页面结果列表中点击某个工作包，When 联动完成，Then `wp-selector` 更新为 `workpackage_id@version` 且蓝图面板展示对应内容。

## Additional Context

### Dependencies

- FastAPI / Pydantic / SQLAlchemy / psycopg2
- PostgreSQL（docker pg，禁止 fallback 到本机 PG）
- 现有 runtime 页面模板与观测路由
- 现有 `governance.workpackage_publish` 表（用于兼容旧路径）；本需求新增独立 workpackage CRUD 实体表或等效存储结构

### Testing Strategy

- API 层（先失败后实现）：
  - 新增 `test_runtime_workpackage_crud_api_contract.py`，覆盖 CRUD 主路径与错误路径。
  - 新增 `test_runtime_workpackage_seed_data_api.py`，覆盖 seed 分布与幂等。
- Web 层（纯 Web E2E）：
  - 新增 `test_runtime_observability_workpackage_search_ui.py`，覆盖检索、过滤、重置、联动。
- 回归层：
  - 运行现有 runtime 相关关键回归，确保新增 CRUD 不破坏 `workpackage-pipeline/events/blueprint` 与 `agent-chat`。
- 数据覆盖要求：
  - 至少 12 条工作包记录；
  - 至少 3 组同 ID 多版本；
  - 至少 2 条中文名、2 条英文名记录。

### Notes

- 高风险项 1：当前 repository 以“发布记录”为中心，新增 CRUD 实体需避免与 publish 语义混淆。
- 高风险项 2：页面已有 pipeline 列表与 selector 联动，新增检索区需避免双数据源不一致。
- 高风险项 3：测试环境 DB 权限可能影响审计写入（`audit` schema），测试需最小化对无关审计依赖。
- 约束：严格遵守 no-fallback/no-mock/no-workground；真实链路失败时返回阻塞与错误，不伪造成功。
- 已完成 Step 3，等待 Step 4 审阅定版。
