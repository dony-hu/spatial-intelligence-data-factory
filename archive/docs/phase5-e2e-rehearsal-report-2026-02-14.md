# Phase-5 端到端演练报告（2026-02-14）

## 演练目标
验证工艺专家 Agent 在 LLM 驱动下完成：
1. 生成工艺草案
2. 编译 process_spec 与工具脚本
3. 发布工艺版本
4. 查询发布结果

## 执行入口
- 脚本：`scripts/run_process_expert_closed_loop.sh`
- Agent 服务：`tools/agent_server.py` (`/api/v1/process/expert/chat`)

## 本次运行结果
- Health：通过
- Draft 生成：通过
  - `draft_id`: `draft_b5c4fd0468`
  - `process_code`: `PROC_F019E7`
  - `domain`: `verification`
- 发布：通过
  - `process_definition_id`: `procdef_6713978c6bb0`
  - `process_version_id`: `procver_b5d9c4cd89a5`
  - `version`: `1.0.1`
  - `status`: released

## 关键观测
- LLM 连通已验证（ARK + `doubao-seed-2-0-mini-260215`）。
- 解析容错已增强（`tools/agent_cli.py`），避免非数字字段导致崩溃。
- 本次发布回合中，LLM 解析出 `execute=true`，因此直接执行发布，未进入 `pending_confirmation`。

## 剩余差距（进入下一迭代）
1. **门禁一致性**：需要在服务端强制写操作默认 `execute=false`，仅确认后执行，避免模型输出绕过门禁。
2. **工具编译完整性**：
   - `DATA_GENERATION` 步骤工具未映射（unknown step）
   - `OUTPUT_PERSIST` 生成器存在 `name 'self' is not defined`
3. **真实核实深度**：当前已进入“流程表达”，但仍需将真实源适配器接入发布包并加入回归测试。

## 结论
- Phase-5 闭环主链路已跑通（设计→编译→发布→可查询）。
- 下一阶段应优先修复“门禁强制策略”和“工具生成失败项”，再做生产级发布。

## 本次新增资产（面向地址产线全逻辑迭代）
- 设计假设与审计驱动框架：`docs/address-line-design-hypothesis-and-audit-cases-2026-02-14.md`
- 结构化质量审计用例：`testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json`
- 测试数据目录登记：`testdata/catalog.yaml`

### 适用说明
- 图中依赖人工标注的工序暂不自动化。
- 人工运营中的“互联网源核实”等可训练工序已纳入用例与能力映射。
- 后续可直接将上述用例输入工艺专家 Agent，执行“审计失败 -> LLM重编译 -> 回归复跑”的闭环。

## 审计回归执行入口（新增）
- 脚本：`scripts/run_address_line_quality_audit.py`
- 默认用例：`testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json`

> 当前版本治理约束：地址产线按“离线工具包模式”运行，默认禁用 LLM 治理回归。
> 产线能力只能来自本地工具包，不应内置地域先验知识。

示例：

```bash
cd /Users/huda/Code/worktrees/factory-address-verify
/Users/huda/Code/.venv/bin/python scripts/run_address_line_quality_audit.py \
  --base-url http://127.0.0.1:8081 \
  --cases-file testdata/fixtures/address-line-quality-audit-cases-2026-02-14.json
```

输出：
- `output/address_line_quality_audit_<timestamp>.json`
- `output/address_line_quality_audit_<timestamp>.md`
