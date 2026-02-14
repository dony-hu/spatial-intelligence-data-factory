# 工厂现状 vs 目标闭环：推进清单（地址真实核实能力）

> 更新说明（2026-02-14）：本文件保留历史推进脉络。最新地址治理方案已升级为“目标态分阶段路线（非仅MVP）”，请优先参考：
>
> - `docs/address-governance-postgres-openhands-design-2026-02-14.md`
> - `docs/address-governance-postgres-openhands-implementation-plan-2026-02-14.md`

## 目标约束
- 工艺方案必须由**工艺专家Agent + LLM**自动生成。
- Coding Agent 不直接实现产线业务逻辑。
- 所有写操作遵循 `pending_confirmation -> /api/v1/confirmation/respond`。

## 5阶段推进

### 阶段1：打通 Agent-LLM 调用链
**目标**：确保 `process_expert/chat` 能稳定连通 LLM 并返回可解析 JSON。

- [x] 补齐 `tools/agent_cli.py`（load_config/run_requirement_query/parse_plan_from_answer）
- [x] 提供配置样例 `config/llm_api.json.example`
- [ ] 部署真实 `config/llm_api.json`（由环境注入密钥）
- [ ] 通过 `/api/v1/process/expert/chat` 完成一次 `design_process` 对话回合

**验收**
- Agent 返回包含 `intent`、`tool_result.compilation.process_spec`、`tool_result.compilation.tool_scripts`。

### 阶段2：基于测试用例自动找方案
**目标**：工艺专家Agent读取测试用例，自动给出“真实核实”工艺草案。

输入建议：
- 使用 `si-factory-public-security-address/testdata/address_line_cases_extended.json`（103条）

输出要求：
- 生成工艺草案（draft）
- 明确步骤：输入校验、标准化、在线核实、冲突仲裁、证据落盘、质量评估
- 生成对应工具脚本到 `tools/generated_tools/`

**验收**
- `compilation.execution_readiness` 为 `ready` 或 `partial`
- 如 `partial`，必须返回缺失能力清单（例如外部密钥/数据源）

### 阶段3：发布链路补齐（工包化）
**目标**：将 Agent 编译产物纳入工厂发布链路。

需要新增工件（由 Agent 触发产出）：
- `workpackages/wp-public-security-address-v0.2.0.json`
- `workpackages/bundles/public-security-address-v0.2.0/`（process/tool/observability）

发布动作：
- `create_process`（确认后执行）
- `create_version`（确认后执行）
- `publish_draft`（确认后执行）

**验收**
- 工包包含 `line_feedback_contract`、`observability_bundle`、`rollback`。

### 阶段4：真实地址核实能力接入
**目标**：从规则打分升级为“规则+真实核验”双轨。

核实能力要求：
- 至少 1 个权威核验源 + 1 个外部地图核验源
- 输出证据包：source/verdict/score/captured_at
- 输出冲突码与降级状态：`SOURCE_CONFLICT`、`MISSING_CAPABILITY`

建议扩展：
- 在 `tools/address_verification.py` 中将模拟源替换为真实 adapter（HTTP/DB）
- 在工艺质量规则中新增核验权重

**验收**
- 对 103 条测试样本可区分 `VERIFIED_EXISTS / VERIFIED_NOT_EXISTS / UNVERIFIABLE_ONLINE`
- 不可核实项进入回放/人工池并可追踪

### 阶段5：端到端演练与发布门禁
**目标**：从 Agent 对话到工包下发全链路可复现。

- 启动 Agent Server
- 通过 `process/expert/chat` 发起设计
- 执行确认接口完成发布
- 验证产线消费工包并产出结果

**验收**
- 全流程日志留痕（会话、确认、版本、发布、回滚目标）
- 形成一次可回放演练记录

## 风险与门禁
- 若 LLM 不可用：禁止进入发布动作，仅保留草案态。
- 若真实核验源不可用：状态必须为 `UNVERIFIABLE_ONLINE`，禁止误判为存在。
- 未走确认机制的写操作一律视为流程违规。
