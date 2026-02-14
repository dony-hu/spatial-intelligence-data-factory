# Process Expert Agent 闭环 API 操作手册

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

## 3. 触发发布请求（先挂起确认）

```bash
curl -sS -X POST http://127.0.0.1:8081/api/v1/process/expert/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "action":"chat",
    "session_id":"session_closed_loop_001",
    "message":"发布草案 draft_id=<替换成实际draft_id>"
  }'
```

期望返回：
- `tool_result.status = pending_confirmation`
- `tool_result.confirmation_id`

## 4. 显式确认写操作

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
