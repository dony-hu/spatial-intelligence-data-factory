# Process Expert Agent 半自动（人工+LLM）API 操作手册

> 架构决策更新（2026-02-14）：停止“工艺Agent自举多轮自动迭代升级”，统一采用“LLM生成草案 + 人工评审决策 + 写操作确认门禁”的半自动模式。

## 0. 前置条件
- 已安装 Python 3.9+
- 设置 LLM 参数（推荐用环境变量）

```bash
export LLM_MODEL="gpt-4o-mini"
export LLM_API_KEY="<your-key>"
# 可选
export LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
export LLM_TIMEOUT_SEC="60"
```

或创建 `config/llm_api.json`（可参考 `config/llm_api.json.example`）。

## 1. 启动 Agent Server

```bash
PYTHONPATH=/Users/huda/Code/worktrees/factory-address-verify \
/Users/huda/Code/.venv/bin/python \
/Users/huda/Code/worktrees/factory-address-verify/tools/agent_server.py \
  --port 8081 \
  --config /Users/huda/Code/worktrees/factory-address-verify/config/llm_api.json \
  --runtime-db /Users/huda/Code/worktrees/factory-address-verify/database/agent_runtime.db \
  --runtime-store /Users/huda/Code/worktrees/factory-address-verify/runtime_store
```

健康检查：

```bash
curl -sS http://127.0.0.1:8081/healthz
```

## 2. 工艺专家Agent设计草案（LLM驱动）

```bash
curl -sS -X POST http://127.0.0.1:8081/api/v1/process/expert/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "action":"design",
    "requirement":"请基于公安地址治理测试用例设计真实地址核实工艺，包含在线核实、冲突仲裁、证据链输出。",
    "domain":"verification"
  }'
```

期望返回字段：
- `draft_id`
- `compilation.process_spec`
- `compilation.tool_scripts`
- `compilation.execution_readiness`

## 3. 触发发布建议（人工评审阶段）

```bash
curl -sS -X POST http://127.0.0.1:8081/api/v1/process/expert/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "action":"chat",
    "session_id":"session_human_loop_001",
    "message":"请评估发布草案 draft_id=<替换成实际draft_id> 的风险并给出建议，不要直接执行写操作"
  }'
```

期望返回：
- 方案建议、风险说明、人工决策提示
- 如进入写操作，返回 `tool_result.status = pending_confirmation` 与 `tool_result.confirmation_id`

## 4. 人工确认后再执行写操作

```bash
curl -sS -X POST http://127.0.0.1:8081/api/v1/confirmation/respond \
  -H 'Content-Type: application/json' \
  -d '{
    "confirmation_id":"<替换成实际confirmation_id>",
    "response":"confirm"
  }'
```

取消发布可用：

```bash
curl -sS -X POST http://127.0.0.1:8081/api/v1/confirmation/respond \
  -H 'Content-Type: application/json' \
  -d '{
    "confirmation_id":"<替换成实际confirmation_id>",
    "response":"reject"
  }'
```

## 5. 查询结果

```bash
# 查询工艺定义
curl -sS -X POST http://127.0.0.1:8081/api/v1/process/expert/chat \
  -H 'Content-Type: application/json' \
  -d '{"action":"query","question":"查询工艺"}'

# 查询版本
curl -sS -X POST http://127.0.0.1:8081/api/v1/process/expert/chat \
  -H 'Content-Type: application/json' \
  -d '{"action":"query","question":"查询版本"}'
```

## 常见故障
- `LLM model is missing`：未配置 `LLM_MODEL` 或 config.model
- `LLM api_key is missing`：未配置 `LLM_API_KEY` 或 config.api_key
- `pending_confirmation` 一直未执行：未调用 `/api/v1/confirmation/respond`
- 发送了无效 action：请使用 `action=design` 或 `action=chat`

## 6. 推荐脚本入口（半自动）

```bash
cd /Users/huda/Code/worktrees/factory-address-verify

# 第一步：生成LLM草案 + 人工决策模板
/Users/huda/Code/.venv/bin/python scripts/run_process_expert_human_loop.py \
  --requirement "请根据测试用例设计真实地址核实工艺草案" \
  --output-dir output/process_expert_human_loop

# 第二步：人工编辑 run_dir/human_decision_template.json 后，作为 decision-file 回放增量修改
/Users/huda/Code/.venv/bin/python scripts/run_process_expert_human_loop.py \
  --requirement "请根据测试用例设计真实地址核实工艺草案" \
  --decision-file <上一步run_dir>/human_decision_template.json \
  --output-dir output/process_expert_human_loop
```
