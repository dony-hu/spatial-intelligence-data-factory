# [已废弃] 工厂现状 vs 目标闭环：推进清单（地址真实核实能力）

> **⚠️ 重要说明（2026-02-19）**
> 本文档已废弃，仅作为历史参考。
> 最新设计请参考：[spec.md](spec.md)
> 
> **主要变更点：**
> 1. **交互方式**：废弃 `/api/v1/process/expert/chat` 和 `/api/v1/confirmation/respond`，统一使用工厂 Agent 的 `converse()` 接口。
> 2. **数据源管理**：引入 `TrustHub` 管理 API Key，不再直接依赖环境变量注入。
> 3. **工包结构**：采用新的 `bundles/<name>-<version>/` 结构，包含 `skills/`、`scripts/`、`entrypoint.sh` 等。
> 4. **流程简化**：简化为 Story 1（可信度验证）和 Story 2（生命周期管理）。

---

## 历史内容（仅供参考）

### 目标约束
- 工艺方案必须由**工艺专家Agent + LLM**自动生成。
- Coding Agent 不直接实现产线业务逻辑。
- 所有写操作遵循 `converse()` 对话确认机制。

### 5阶段推进（已由 Story 1 & 2 替代）

#### 阶段1：打通 Agent-LLM 调用链
**目标**：确保 `converse()` 能稳定连通 LLM。

- [x] 补齐 `packages/factory_agent/agent.py`
- [x] 提供 `converse()` 接口
- [x] 通过 CLI 完成一次 `design_process` 对话回合

#### 阶段2：基于测试用例自动找方案
**目标**：工艺专家Agent读取测试用例，自动给出“真实核实”工艺草案。

输入建议：
- 使用 `si-factory-public-security-address/testdata/address_line_cases_extended.json`（103条）

输出要求：
- 生成工艺草案（draft）
- 明确步骤：输入校验、标准化、在线核实、冲突仲裁、证据落盘、质量评估
- 生成对应工具脚本到 `workpackages/bundles/.../scripts/`

#### 阶段3：发布链路补齐（工包化）
**目标**：将 Agent 编译产物纳入工厂发布链路。

需要新增工件（由 Agent 触发产出）：
- `workpackages/bundles/poi-trust-verification-v1.0.0/`

发布动作：
- `generate_workpackage`（确认后执行）
- `release_workpackage`（确认后执行）

#### 阶段4：真实地址核实能力接入
**目标**：从规则打分升级为“规则+真实核验”双轨。

核实能力要求：
- 至少 1 个权威核验源 + 1 个外部地图核验源（通过 `TrustHub` 管理）
- 输出证据包：source/verdict/score/captured_at

建议扩展：
- 在 `scripts/verify_poi.py` 中实现真实 adapter（HTTP/DB）

#### 阶段5：端到端演练与发布门禁
**目标**：从 Agent 对话到工包下发全链路可复现。

- 启动 Factory CLI
- 通过 `converse()` 发起设计
- 执行确认接口完成发布
- 验证产线消费工包并产出结果

**验收**
- 全流程日志留痕
- 形成一次可回放演练记录

## 风险与门禁
- 若 LLM 不可用：禁止进入发布动作，仅保留草案态。
- 若真实核验源不可用：状态必须为 `UNVERIFIABLE_ONLINE`，禁止误判为存在。
