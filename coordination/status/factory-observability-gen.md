# Factory-Observability-Gen 任务卡

- 任务卡：`TC-05`（产线观测代码生成）
- 轮次：`2026-02-14`
- Done：
  - 已在 `tools/process_compiler/tool_generator.py` 接入观测自动生成：编译时自动产出 `line_observe.py` 与 `line_metrics.json`。
  - 已在 `tools/process_compiler/step_identifier.py` 为步骤补齐标准 `error_code` 字段，并同步写入观测指标文件 `step_error_codes`。
  - 已在 `tools/process_compiler/compiler.py` 串联 `observability_bundle` 回传，并写入 `process_spec.observability_bundle`。
  - 已在 `tools/agent_server.py`、`tools/process_tools/design_process_tool.py`、`tools/process_tools/modify_process_tool.py` 透出 `observability_bundle`。
  - 已新增测试 `tests/test_process_compiler_observability.py`，并通过 `python3 -m unittest tests.test_process_compiler_observability tests.test_workflow_line_metrics`。
- Next：
  - 将自动生成的观测包挂接到正式 `wp-*.json` 发布流，替换示例包中的静态路径配置。
  - 补充失败路径回放用例，校验 `line_observe.py` 在 `status != PASS` 时输出错误码。
- Blocker：无
- ETA：`2026-02-14` 18:30 前完成发布流挂接与失败路径回放用例
- Artifacts：
  - `observability/l3/line_observability_spec.md`
  - `workpackages/bundles/address-topology-v1.0.1/observability/line_observe.py`
  - `workpackages/bundles/address-topology-v1.0.1/observability/line_metrics.json`
