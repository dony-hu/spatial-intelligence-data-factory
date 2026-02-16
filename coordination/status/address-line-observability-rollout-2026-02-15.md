# 地址治理产线可观测落地回执（2026-02-15）

## 目标
让管理层在观测系统中直接看到地址治理产线运行状态。

## 本轮交付
1. 接入最小指标（已上屏）
   - 任务状态：`address_line.task_status`
   - 质量分：`address_line.quality_score`
   - 失败回放引用：`address_line.failure_replay_refs[]`
   - 样本关联观测：`address_line.sample_trace_links[]`
2. 可观测页面
   - 页面入口：`/v1/governance/lab/observability/view`
   - 页面区块：`地址治理产线最小指标`、`失败回放引用`、`样本到观测记录关联`
3. 证据
   - 截图文件：`output/observability/address_line_observability_demo_20260215_201023.png`
   - 截图包含时间：页面顶部 `最后刷新` 字段
   - 样本追踪文件：`output/observability/address_line_sample_trace_20260215_201023.json`

## 代码位置
- 指标聚合：`services/governance_api/app/routers/lab.py` (`_address_line_metrics`, `_build_observability_snapshot`)
- 页面渲染：`services/governance_api/app/routers/lab.py` (`observability_live_view`)
- 集成测试：`services/governance_api/tests/test_observability_integration.py`
- E2E 测试：`tests/web_e2e/test_observability_live_ui.py`

## 字段说明文档
- `docs/address-line-observability-fields-2026-02-15.md`

## 演示路径说明
- `coordination/status/address-line-observability-demo-path-2026-02-15.md`
