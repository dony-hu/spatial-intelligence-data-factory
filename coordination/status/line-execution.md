# 子线状态：产线执行

- 进度：100%
- Done：
  - WP-003-B R2 Gate Closure 已闭环：workpackage schema、line feedback contract、failure replay 回传三门槛均进入阻断判定。
  - 产线回传改为真实消费 `line_feedback_contract`：`scripts/line_execution_tc06.py feedback` 直接读取 workpackage 合同生成回传，禁止手写自由字段。
  - 已完成回归测试：
    - `tests/test_run_p0_workpackage.py`（3/3 通过）
    - `tests/test_tc06_line_execution.py`（4/4 通过）
  - 已完成真实 line run 证据链（输入 -> 失败 -> replay -> 回传）：
    - 输入并失败：`output/line_runs/tc06_single_run_2026-02-15_191054_655590.json`
    - 失败队列快照：`output/line_runs/failed_replay_queue.json`
    - replay 结果：`output/line_runs/tc06_failure_replay_2026-02-15_191054_638511.json`
    - 工厂回传：`output/workpackages/line_feedback.latest.json`
    - gate 判定：`output/workpackages/wp-core-engine-p0-stabilization-v0.1.0.report.json`
  - 已验证“门槛失败即阻断发布”：缺失回传输入时 `scripts/run_p0_workpackage.py` 返回 `NO_GO` 且退出码 `1`。
  - 已完成 pre-release checklist 落地（v1.0.1 / v1.0.2）：`output/workpackages/pre_release_checklist.wp-address-topology-v1.0.1_v1.0.2.md`
  - 已生成回传防篡改 hash：`output/workpackages/line_feedback.latest.sha256`
  - 已完成任务批次状态回写：`dispatch-address-line-closure-001`（2026-02-15 20:33 CST）
  - 已完成任务批次状态回写：`dispatch-address-line-closure-002`（2026-02-15 21:04 CST）
  - 已产出当次新鲜证据链（非历史复用）：
    - 成功样本：`output/line_runs/tc06_single_run_2026-02-15_210323_668618.json`
    - 失败样本：`output/line_runs/tc06_single_run_2026-02-15_210323_689989.json`
    - 回放样本：`output/line_runs/tc06_failure_replay_2026-02-15_210327_583381.json`
    - 批次状态：`output/workpackages/dispatch-address-line-closure-002.status.json`
  - 已完成 CI 强阻断接入（`line_feedback.latest.sha256`）：
    - workflow 触发已覆盖 `output/workpackages/line_feedback.latest.json` 与 `output/workpackages/line_feedback.latest.sha256`
    - workflow 新增硬阻断步骤：`python scripts/run_p0_workpackage.py --skip-package-tests`
    - workflow 新增阻断演示步骤：`python scripts/run_line_feedback_ci_block_demo.py`
  - 已产出阻断演示证据（篡改 hash => NO_GO + exit code 1）：
    - `output/workpackages/line_feedback_ci_block_demo.latest.json`
    - `output/workpackages/line_feedback_ci_block_demo.latest.md`
  - 已完成任务批次状态回写：`dispatch-address-line-closure-004`（2026-02-15 22:45 CST）
- Next：
  - 持续执行当次新鲜样本抽检，防止回归到历史证据复用。
- Blocker：无
- ETA：持续滚动（已完成 CI 校验自动化接入）

## 回传字段固定格式与引用规则（WP-003-B）

1. 固定字段（必须同时存在）：  
   `status` / `done` / `next` / `blocker` / `eta` / `test_report_ref` / `failure_queue_snapshot_ref` / `replay_result_ref` / `release_decision`
2. 固定引用格式（schema + gate 双重校验）：  
   - `failure_queue_snapshot_ref`: `sqlite://<path>#failure_queue`  
   - `replay_result_ref`: `sqlite://<path>#replay_runs`
3. 固定引用一致性规则：  
   - `line_feedback.latest.json` 中两个 ref 必须与 workpackage 的 `line_feedback_contract` 完全一致。  
   - 任何不一致或格式不符，`line_feedback_contract_enforced=false`，发布判定直接 `NO_GO`。
4. 固定“真实消费”规则：  
   - 回传文件由 `scripts/line_execution_tc06.py feedback` 从 workpackage 合同生成。  
   - `scripts/run_p0_workpackage.py` 不再生成/补写失败队列与 replay 表，仅验证真实产线数据（表存在且行数 > 0）。
