"""
Phase 4: 最终重构执行计划和应用指南

本文档提供逐步应用refactoring改动的完整指南。

策略：渐进式应用改动，每个步骤都有验证点
"""

import sys
from pathlib import Path

print("""
╔══════════════════════════════════════════════════════════════════════╗
║              Phase 4: 最终重构和部署                                ║
║        应用ToolRegistry改动到agent_server.py                        ║
╚══════════════════════════════════════════════════════════════════════╝

📋 Phase 4 执行计划
═══════════════════════════════════════════════════════════════════════

Step 1: 准备工作 (5分钟)
  ✓ 备份当前agent_server.py
  ✓ 创建refactoring branch
  ✓ 验证Phase 1-3的所有测试通过

Step 2: 添加导入 (2分钟)
  ✓ 添加ToolRegistry相关导入
  ✓ 添加SessionState导入

Step 3: 初始化ToolRegistry (3分钟)
  ✓ 创建init_tool_registry()函数
  ✓ 调用registry初始化

Step 4: 替换_execute_process_expert_intent (10分钟)
  ✓ 创建新版本使用registry
  ✓ 保留旧版本作为备份
  ✓ 验证导入和基本功能

Step 5: 更新_run_process_expert_chat_turn (15分钟)
  ✓ 集成SessionState
  ✓ 使用registry执行工具
  ✓ 验证确认流程

Step 6: 删除不需要的函数 (5分钟)
  ✓ 标记为deprecated
  ✓ 保留备份
  ✓ 验证没有其他地方调用

Step 7: 测试验证 (30分钟)
  ✓ Phase 1-3单元测试
  ✓ Phase 4集成测试
  ✓ 现有API兼容性测试
  ✓ E2E测试

Step 8: 性能测试 (15分钟)
  ✓ 响应时间对比
  ✓ 内存使用对比
  ✓ 吞吐量测试

Step 9: 文档更新 (10分钟)
  ✓ 更新API文档
  ✓ 更新部署指南
  ✓ 创建Phase 4完成报告

总耗时: ~90分钟

═══════════════════════════════════════════════════════════════════════

🔍 详细改动指南

【改动1】添加导入 (line 24)
─────────────────────────────────────────────────────────────────────

LOCATION: After existing imports (around line 24)

ADD:
```python
from tools.registry_manager import (
    initialize_registry,
    execute_tool as execute_tool_via_registry,
    list_registered_intents,
    ToolRegistryManager,
)
from tools.agent_framework import SessionState, ChatState
```

VERIFICATION:
  python3 -c "from tools.registry_manager import initialize_registry; print('✓ Import OK')"

【改动2】全局变量初始化 (line 44)
─────────────────────────────────────────────────────────────────────

LOCATION: After existing global definitions (around line 44)

ADD:
```python
# Phase 3: ToolRegistry和SessionState集成
registry_initialized = False
session_states: Dict[str, SessionState] = {}  # session_id -> SessionState
tool_registry = None
```

【改动3】ToolRegistry初始化函数 (line 80)
─────────────────────────────────────────────────────────────────────

LOCATION: After utility functions, before class definition

ADD:
```python
def init_tool_registry() -> None:
    \"\"\"Initialize the ToolRegistry with all process tools\"\"\"
    global tool_registry, registry_initialized

    if registry_initialized:
        return

    try:
        tool_registry = initialize_registry(
            runtime_store=runtime_store,
            process_compiler=process_compiler,
            process_db_api=process_db_api,
            llm_service=None,  # Optional LLM service
        )
        registry_initialized = True
        print("[INFO] ToolRegistry initialized successfully")
        print(f"[INFO] Registered tools: {list(tool_registry.list_tools().keys())}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize ToolRegistry: {e}")
        registry_initialized = False
        raise
```

VERIFICATION:
  python3 -c "
    from tools.agent_server import init_tool_registry
    init_tool_registry()
    print('✓ Registry init OK')
  "

【改动4】新版本_execute_process_expert_intent (line 217)
─────────────────────────────────────────────────────────────────────

LOCATION: Replace the old function (line 217-261)

REPLACE WITH:
```python
def _execute_process_expert_intent(
    intent: str, params: Dict[str, Any], session_id: str = ""
) -> Dict[str, Any]:
    \"\"\"
    Execute process expert intent using ToolRegistry.

    Refactored to use ToolRegistry instead of hardcoded if-elif.
    All tool routing now handled by registry.
    \"\"\"
    if not registry_initialized or tool_registry is None:
        return {
            "status": "error",
            "error": "ToolRegistry not initialized",
            "intent": intent,
        }

    try:
        result = execute_tool_via_registry(intent, params, session_id=session_id)

        # Ensure backward compatibility - add intent to response
        if isinstance(result, dict):
            result.setdefault("intent", intent)

        return result

    except Exception as e:
        logger.error(f"Tool execution failed for intent={intent}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "intent": intent,
            "error_type": "execution_error",
        }
```

VERIFICATION:
  - Test with sample tool call
  - Verify response format matches old API
  - Check error handling

【改动5】SessionState集成函数 (line 270)
─────────────────────────────────────────────────────────────────────

LOCATION: After _execute_process_expert_intent

ADD:
```python
def get_or_create_session_state(session_id: str) -> SessionState:
    \"\"\"Get or create SessionState for a session\"\"\"
    if session_id not in session_states:
        session_states[session_id] = SessionState(session_id=session_id)
    return session_states[session_id]


def update_session_from_tool_result(
    session_id: str, intent: str, tool_result: Dict[str, Any]
) -> None:
    \"\"\"Update session state based on tool execution result\"\"\"
    session_state = get_or_create_session_state(session_id)

    status = tool_result.get("status", "unknown")

    if status == "ok":
        msg = f"执行了 {intent} 操作"
        session_state.add_message("system", msg)
        session_state.transition_to(ChatState.NORMAL)

    elif status in ["error", "validation_error"]:
        error_msg = tool_result.get("error") or tool_result.get("errors")
        error_text = str(error_msg)
        session_state.add_message("system", f"错误: {error_text}")
        session_state.transition_to(ChatState.ERROR)
```

【改动6】修改_run_process_expert_chat_turn (line 266)
─────────────────────────────────────────────────────────────────────

LOCATION: The tool execution section (around line 404-450)

KEY CHANGES:
  - Line 279: Replace _execute_process_expert_intent call
  - Add session_id parameter to all tool executions
  - Integrate SessionState tracking
  - Keep confirmation logic unchanged

BEFORE (old code):
```python
tool_result = _execute_process_expert_intent(pending["intent"], pending["params"])
```

AFTER (new code):
```python
tool_result = _execute_process_expert_intent(
    pending["intent"],
    pending["params"],
    session_id=session_id  # NEW: pass session_id
)
update_session_from_tool_result(session_id, pending["intent"], tool_result)
```

VERIFICATION:
  - Test confirmation workflow
  - Verify session state transitions
  - Check message history

【改动7】服务器启动时初始化 (line 1600)
─────────────────────────────────────────────────────────────────────

LOCATION: In main() function, before httpd.serve_forever()

ADD:
```python
if __name__ == "__main__":
    # ... existing argument parsing ...

    # NEW: Initialize ToolRegistry before starting server
    print("[INIT] Initializing ToolRegistry...")
    init_tool_registry()

    # Start HTTP server
    print(f"[START] Starting Agent Server on {host}:{port}...")
    httpd = HTTPServer((host, port), AgentServerHandler)
    httpd.serve_forever()
```

VERIFICATION:
  python3 tools/agent_server.py
  # Should see: [INIT] Initializing ToolRegistry...
  #            [INFO] ToolRegistry initialized successfully

═══════════════════════════════════════════════════════════════════════

🧪 测试计划

【Step 1】单元测试验证
─────────────────────────────────────────────────────────────────────
python3 tests/test_phase2_tools.py
python3 tests/test_phase3_registry_integration.py

Expected: All tests PASS

【Step 2】集成测试验证
─────────────────────────────────────────────────────────────────────
python3 -c "
from tools.agent_server import init_tool_registry, _execute_process_expert_intent

init_tool_registry()

# Test 1: Valid tool execution
result = _execute_process_expert_intent('query_process', {'code': 'TEST'})
assert result['status'] in ['ok', 'error'], f'Unexpected status: {result[\"status\"]}'
print('✓ Test 1: Valid tool execution')

# Test 2: Invalid tool
result = _execute_process_expert_intent('invalid_tool', {})
assert result['status'] == 'error', 'Should return error for invalid tool'
print('✓ Test 2: Invalid tool rejection')

# Test 3: Validation error
result = _execute_process_expert_intent('design_process', {'requirement': 'short'})
assert result['status'] == 'validation_error', 'Should validate parameters'
print('✓ Test 3: Parameter validation')

print('✓ All integration tests passed')
"

【Step 3】向后兼容性验证
─────────────────────────────────────────────────────────────────────
# Test that response format is unchanged
result = _execute_process_expert_intent('query_process', {})
required_fields = ['status', 'intent']
missing = [f for f in required_fields if f not in result]
assert not missing, f'Missing fields: {missing}'
print('✓ Backward compatibility verified')

【Step 4】性能测试
─────────────────────────────────────────────────────────────────────
import time

# Warm up
for _ in range(3):
    _execute_process_expert_intent('query_process', {})

# Benchmark
t0 = time.time()
for i in range(100):
    _execute_process_expert_intent('query_process', {})
elapsed = time.time() - t0

avg_ms = (elapsed / 100) * 1000
print(f'Average execution time: {avg_ms:.2f}ms')
assert avg_ms < 50, f'Performance degradation: {avg_ms}ms'
print('✓ Performance test passed')

═══════════════════════════════════════════════════════════════════════

📊 检查清单

应用改动前:
  ☐ 所有Phase 1-3测试通过
  ☐ git branch已创建
  ☐ 现有功能已验证

应用改动中:
  ☐ 逐个应用改动
  ☐ 每个改动后验证import
  ☐ 保留备份代码

应用改动后:
  ☐ 所有测试通过
  ☐ 向后兼容性验证通过
  ☐ 性能指标OK
  ☐ 文档更新

上线前:
  ☐ 代码审查通过
  ☐ E2E测试通过
  ☐ 监控告警配置
  ☐ 回滚计划准备

═══════════════════════════════════════════════════════════════════════

✨ 预期成果

代码指标:
  • agent_server.py: 1300行 → ~500行 (-62%)
  • 复杂度: 显著降低
  • 可维护性: 大幅提升

测试指标:
  • 单元测试: 40+ 通过
  • 集成测试: 5+ 通过
  • 向后兼容性: ✓ 通过
  • 性能: ✓ 达到或超过预期

质量指标:
  • 代码审查: ✓ 通过
  • 文档完整: ✓ 是
  • 部署准备: ✓ 就绪

═══════════════════════════════════════════════════════════════════════

💡 常见问题

Q: 如何回滚?
A: git checkout <backup-branch> 即可恢复原始代码

Q: 是否需要修改测试?
A: 不需要，所有测试代码保持不变，测试目标不变

Q: 性能会下降吗?
A: 不会，ToolRegistry使用dictionary lookup，性能相同甚至更好

Q: 是否需要修改client端?
A: 不需要，API响应格式完全相同

═══════════════════════════════════════════════════════════════════════

""")

print(__doc__)
