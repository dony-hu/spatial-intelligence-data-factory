# S2-15 最小测试清单（Dev/QA 执行版）

## 1. 执行目标

为 `OBS-RUNTIME-S2-15` 提供最小可执行测试路径，确保“人工门禁 + 按工作包执行 + 中文事件可读”可验证、可回归。

## 2. 环境前置

1. 使用 PG 数据库运行测试（禁止 SQLite 主链路）。
2. 默认命令前缀：`PYTHONPATH=. .venv/bin/pytest -q`
3. 若 `.venv/bin/pytest` 不存在，先安装 `pytest` 并重跑。

## 3. 现有必须回归（先跑）

1. `services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py`
- 覆盖：工作包链路阶段与字段契约。

2. `services/governance_api/tests/test_runtime_workpackage_events_api_contract.py`
- 覆盖：`workpackage-events` 结构与事件字段。

3. `services/governance_api/tests/test_runtime_llm_interactions_api_contract.py`
- 覆盖：多轮交互统计与字段契约。

4. `services/governance_api/tests/test_runtime_upload_batch.py`
- 覆盖：上传批次基础行为（当前以 `ruleset_id` 路径为主）。

5. `services/governance_api/tests/test_runtime_workpackage_observability_rbac.py`
- 覆盖：链路接口 RBAC 与脱敏约束。

6. `services/governance_api/tests/test_runtime_compliance_rbac.py`
- 覆盖：运行态合规审计相关 RBAC 行为。

7. `tests/web_e2e/test_runtime_observability_workpackage_pipeline_ui.py`
- 覆盖：页面链路下钻主路径。

8. `tests/web_e2e/test_runtime_observability_upload_ui.py`
- 覆盖：上传页面执行交互。

## 4. S2-15 新增必须补测（先失败再实现）

1. 新增：`test_runtime_upload_batch_by_workpackage_contract.py`
- 失败用例：
  - 仅传 `workpackage_id` 不传 `version` -> `400 INVALID_PAYLOAD`
  - 同时传 `workpackage_id/version` 与 `ruleset_id` 且映射冲突 -> `400 INVALID_PAYLOAD`
- 通过用例：
  - 传 `workpackage_id/version` 成功创建任务并可回查。

2. 新增：`test_runtime_workpackage_confirmation_gate.py`
- 失败用例：
  - 无 `confirm_generate` 禁止 `workpackage_packaged`
  - 无 `confirm_publish` 禁止 `runtime_submit_requested`
- 通过用例：
  - 完整确认动作后可进入 `submitted/accepted`。

3. 新增：`test_runtime_workpackage_events_api_contract.py`
- 失败用例：
  - 缺任一中文字段（`source_zh/event_type_zh/status_zh/description_zh/pipeline_stage_zh`）即失败。
- 通过用例：
  - 全链路事件中文字段齐全且非空。

4. 新增：`test_runtime_workpackage_upload_ui_by_workpackage_e2e.py`
- 失败用例：
  - 上传页未提供 `workpackage_id@version` 输入或无效校验。
- 通过用例：
  - 上传 CSV -> 选择 `workpackage_id@version` -> 执行成功 -> 可下钻事件中文时间线。

## 5. 推荐执行顺序

1. 先执行第 3 节回归，确认当前基线。
2. 再按第 4 节逐个新增失败用例并提交。
3. 实现功能后逐个转绿。
4. 最后跑一次全量矩阵并出汇总报告。

## 6. 验收出口

1. 测试报告：`output/test-reports/s2-15-regression-summary-*.md`
2. 验收报告：`docs/acceptance/s2-15-runtime-human-confirmation-and-workpackage-exec-*.json`
3. 验收报告：`docs/acceptance/s2-15-runtime-human-confirmation-and-workpackage-exec-*.md`
