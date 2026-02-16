# Pre-Release Checklist (wp-address-topology-v1.0.1 / v1.0.2)

- 批次ID：dispatch-address-line-closure-001
- 检查时间（本地）：2026-02-15 20:33:19 CST
- 检查时间（UTC）：2026-02-15T12:33:19Z

## Checklist

1. line_feedback 回传文件存在：PASS
   - output/workpackages/line_feedback.latest.json
2. 回传关键字段完整：PASS
   - failure_queue_snapshot_ref
   - replay_result_ref
3. 引用格式符合合同：PASS
   - sqlite://...#failure_queue
   - sqlite://...#replay_runs
4. failure/replay 存储可读且有数据：PASS
   - sqlite://database/tc06_line_execution.db#failure_queue
   - sqlite://database/tc06_line_execution.db#replay_runs
5. 防篡改 hash 生成：PASS
   - output/workpackages/line_feedback.latest.sha256
6. gate 总判定：BLOCKED
   - runtime_unified_3_11_plus=false

## 备注

- 当前链路证据完备，但发布仍受 runtime 门槛阻断。
