# 工程边界合规报告（首份）

- 批次ID：`dispatch-address-line-closure-004`
- 工作线：工程监理线
- 负责人：工程监理-Codex
- 审计时间（本地）：2026-02-15 23:55:00 CST
- 审计范围：跨线边界治理与审计（越界检查 / 抄近路检查 / Hold-Release 建议）

## 一、审计输入与证据来源

1. 派单目标与验收门槛：
   - `coordination/dispatch/iteration-008-bm-master-next-iteration.md`
2. 总控状态与风险口径：
   - `coordination/status/overview.md`
3. 反抄近路制度口径：
   - `coordination/README.md`
4. 当前分支改动面：
   - `git diff --name-only`（共 41 个文件）
5. 核心门槛与审批硬门控实现/测试：
   - `services/governance_api/app/routers/rulesets.py`
   - `services/governance_api/tests/test_rulesets_api.py`
6. 产线回传防篡改执行口径：
   - `coordination/status/line-execution.md`

## 二、越界检查（Boundary Check）

### 2.1 结论

- **结论：部分通过（存在可追溯性缺口，判定为 HOLD 级风险）**

### 2.2 事实与判断

1. 当前批次对工程监理线的目标明确要求发布项目级审计报告与 HOLD/RELEASE 建议。
2. 当前分支存在跨目录复合改动（`git diff --name-only` 共 41 文件），涉及 `packages/`、`services/`、`database/`、`coordination/`、`workpackages/` 等多区域。
3. 工作包约束中存在“按包限定修改范围”的口径（例如：
   - `wp-core-engine-address-core-p0-v0.1.0` 限定 `packages/address_core`
   - `wp-core-engine-governance-api-lab-p0-v0.1.0` 限定 `services/governance_api`
   - `wp-core-engine-trust-data-hub-p0-v0.1.0` 限定 `services/trust_data_hub`）
4. 现有证据可证明“约束被定义”，但**尚缺逐文件的 owner/workpackage 映射清单**，无法在本轮直接证明所有改动均已完成跨线授权闭环。

### 2.3 风险定级

- `R-Boundary-001`：跨线变更可归因证据不足（严重级别：`High`，状态：`Open`）

## 三、抄近路检查（Shortcut Check）

### 3.1 结论

- **结论：通过（未发现 mock 绕过、越权改码、测试篡改的直接证据）**

### 3.2 事实与判断

1. 制度口径明确禁止通过 `mock/桩数据` 绕过真实链路验收。
2. 对当前改动执行差异扫描，未发现新增 `pytest.skip / xfail / mock / monkeypatch` 等抄近路特征。
3. 审批硬门控在实现层与测试层均有增强：
   - 直接 publish 被阻断（`APPROVAL_GATE_REQUIRED`）
   - 未审批/已拒绝/缺失变更单均阻断激活（`APPROVAL_PENDING / APPROVAL_REJECTED / APPROVAL_MISSING`）
4. 产线回传路径声明为“真实消费合同 + hash 防篡改 + 失败即阻断发布”，与反篡改目标一致。

### 3.3 风险定级

- `R-Shortcut-001`：当前未触发（严重级别：`Low`，状态：`Closed`）

## 四、项目级 Hold / Release 建议

### 4.1 建议结论

- **建议：`HOLD`（暂不签发 RELEASE）**

### 4.2 触发依据

1. 夜间门槛风险仍为 `NO_GO`（`suite_web_e2e_catalog` 失败）尚未完成连续修复闭环。
2. 越界审计存在 `R-Boundary-001`：改动归因链缺失，未满足“可追溯证据”验收标准。

### 4.3 Release 前置解锁条件（必达）

1. 提交《逐文件归因清单》：`changed_file -> owner_line -> workpackage_id -> approval_ref`。
2. 完成夜间 `suite_web_e2e_catalog` 连续两次 `passed` 并回写证据。
3. 由工程监理线复核通过后，将 `R-Boundary-001` 从 `Open` 关闭为 `Closed`。

## 五、回写与升级

- 当前批次建议状态：`HOLD`
- 已执行升级动作：将 `R-Boundary-001` 标记为高风险并建议同步至项目管理总控线。
