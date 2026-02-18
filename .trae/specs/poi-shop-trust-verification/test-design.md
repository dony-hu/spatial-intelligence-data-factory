# 空间智能数据工厂 - 智能体增强测试用例设计

## 验收目标
验证工厂 CLI ↔ 工厂 Agent ↔ 数据治理产线的协同，以及工厂 CLI 到可信数据 HUB 的打通。

## 约束与观测项
- **约束**: 整个开发过程不允许直接修改 workpackage 中的内容
- **观测项**: workpackage 中的内容是通过工厂 Agent 生成的

---

## Story 1: 沿街商铺 POI 可信度验证

### Test Case 1.1: 用户自然语言发起请求，智能对话确定 2~3 家可信数据源
**目标**: 验证用户可以通过工厂 CLI 用自然语言发起请求，与工厂 Agent（对接 LLM）智能对话，最终确定 2~3 家外部可信数据源，并提供 API Key
**前置条件**: 无
**步骤**:
1. 用户通过工厂 CLI 用自然语言发起请求，例如：「我希望对沿街商铺 POI 进行可信度验证，帮我找几家可信的外部数据源」
2. 工厂 CLI 调用工厂 Agent 的 converse() 接口进行智能对话
3. 测试程序智能响应对话，最终确定 2~3 家外部可信数据源（不限于图商）
4. 测试程序通过 converse() 对话提供这些数据源的 API Key
5. 用户确认
**预期结果**:
- 测试程序与工厂 Agent 智能对话成功
- 最终确定 2~3 家外部可信数据源
- API Key 存储到可信数据 HUB

---

### Test Case 1.2: 工厂 Agent 生成完整治理工作包（workpackage）
**目标**: 验证工厂 Agent 能基于用户确定的 2~3 家数据源生成完整的治理工作包（workpackage）
**前置条件**: Test Case 1.1 已成功执行
**步骤**:
1. 用户确认 2~3 家数据源和 API Key 后
2. 工厂 CLI 调用工厂 Agent 的 converse() 接口生成工作包
3. 工厂 Agent 生成完整的治理工作包（包含所有脚本、skills、标准工作入口）
**预期结果**:
- 工作包生成成功
- 工作包包含所有脚本、skills 和标准工作入口
- 工作包存储到 `workpackages/` 目录
- **观测项**: workpackage 内容通过工厂 Agent 生成，无直接人工修改

---

### Test Case 1.3: 治理产线执行工作包，调用 2~3 家数据源 API
**目标**: 验证治理产线能执行工作包，并调用 2~3 家数据源 API 进行可信度打分
**前置条件**: Test Case 1.2 已成功执行
**步骤**:
1. 治理产线加载并执行工作包
2. 工作包调用第 1 家数据源 API
3. 工作包调用第 2 家数据源 API
4. （可选）工作包调用第 3 家数据源 API
5. 工作包输出验证结果
**预期结果**:
- 工作包执行成功
- 2~3 家数据源 API 被调用
- 输出验证结果（包含 2~3 家数据源的可信度分数）

---

### Test Case 1.4: Story 1 端到端完整流程（关键验收场景）
**目标**: 验证从用户自然语言发起请求到工作包执行的完整流程
**前置条件**: 无
**步骤**:
1. 用户执行 `python scripts/factory_cli.py`，并用自然语言发起请求
2. 测试程序与工厂 Agent（对接 LLM）通过 converse() 智能对话
3. 最终确定 2~3 家外部可信数据源
4. 测试程序通过 converse() 提供这些数据源的 API Key
5. 用户确认
6. 工厂 Agent 生成工作包
7. 治理产线执行工作包
8. 输出验证结果
**预期结果**:
- 完整流程无报错
- API Key 存储到可信数据 HUB
- 工作包生成并执行成功
- 输出包含 2~3 家数据源可信度分数的验证结果
- **观测项**: workpackage 中所有内容均通过工厂 Agent 生成，无直接人工修改

---

## Story 2: Workpackage 生命周期管理

### Test Case 2.1: Workpackage List & Query
**目标**: 验证工厂 Agent 可以列出和查询系统中所有 workpackage
**前置条件**: 无
**步骤**:
1. 用户通过工厂 CLI 与工厂 Agent converse() 对话，请求 workpackage list
2. 用户通过 converse() 对话查询特定 workpackage
**预期结果**:
- 工厂 Agent 返回 workpackage 列表
- 工厂 Agent 返回特定 workpackage 的详细信息

---

### Test Case 2.2: Workpackage Release（版本发布）
**目标**: 验证工厂 Agent 可以发布 workpackage，在 workpackages/bundles/ 下创建新版本目录
**前置条件**: Test Case 1.2 已成功执行
**步骤**:
1. 用户通过工厂 CLI 与工厂 Agent converse() 对话，执行 workpackage release
2. 工厂 Agent 在 `workpackages/bundles/` 下创建新版本目录
**预期结果**:
- 新版本目录创建成功
- 新版本包含完整的治理脚本、skills 和标准工作入口

---

### Test Case 2.3: Workpackage Dryrun（试运行）
**目标**: 验证工厂 Agent 可以 dryrun workpackage，在发布前试运行测试效果
**前置条件**: Test Case 1.2 已成功执行
**步骤**:
1. 用户通过工厂 CLI 与工厂 Agent converse() 对话，执行 workpackage dryrun
2. 工厂 Agent 试运行测试效果
3. 用户通过工厂 CLI 进行数据处理流程的调试
**预期结果**:
- dryrun 执行成功
- 用户可以通过 CLI 进行调试
