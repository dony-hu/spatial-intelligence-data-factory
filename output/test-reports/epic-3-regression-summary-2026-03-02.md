# Epic 3 回归汇总（2026-03-02）

## 执行命令

```bash
PYTHONPATH=. .venv/bin/pytest -q \
  services/governance_api/tests/test_runtime_reliability_sli_slo.py \
  services/governance_api/tests/test_runtime_freshness_latency.py \
  services/governance_api/tests/test_runtime_quality_drift.py \
  services/governance_api/tests/test_runtime_performance_governance.py \
  services/governance_api/tests/test_runtime_compliance_rbac.py \
  services/governance_api/tests/test_runtime_workpackage_observability_rbac.py \
  services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py \
  services/governance_api/tests/test_runtime_workpackage_events_api_contract.py \
  services/governance_api/tests/test_runtime_llm_interactions_api_contract.py
```

## 结果

- `15 passed in 6.35s`
- 阻断级失败：`0`

## 覆盖面

1. SLI/SLO 与告警评估
2. 新鲜度与端到端延迟
3. 质量漂移检测
4. 性能治理
5. RBAC 与脱敏
6. 工作包链路/事件/LLM 交互契约

## 残余风险

1. UI E2E 在本轮未执行（依赖浏览器测试运行环境），建议发布前补跑。
2. 长压稳定性仍需多批次样本补证据。
