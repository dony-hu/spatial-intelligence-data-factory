"""
Phase 3 Agent Server Refactoring Template

This file shows the exact code changes needed to integrate ToolRegistry
into agent_server.py while maintaining backward compatibility.

Apply these changes incrementally to minimize risk.
"""

# ============================================================================
# CHANGE 1: Add imports (line ~25)
# ============================================================================

# ADD after existing imports:

from tools.registry_manager import (
    initialize_registry,
    execute_tool as execute_tool_via_registry,
    list_registered_intents,
)


# ============================================================================
# CHANGE 2: Initialize ToolRegistry at server startup (line ~75-80)
# ============================================================================

# ADD in the HTTPHandler class initialization or main function:

def init_tool_registry():
    """Initialize the global ToolRegistry"""
    global registry_initialized
    if not registry_initialized:
        try:
            initialize_registry(
                runtime_store=runtime_store,
                process_compiler=process_compiler,
                process_db_api=process_db_api,
                llm_service=None,  # Optional LLM service integration
            )
            registry_initialized = True
            logger.info("ToolRegistry initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ToolRegistry: {e}")
            registry_initialized = False


# ADD global variable before HTTPHandler class:
registry_initialized = False


# CALL during server startup (around line 1600 in main):
#   if __name__ == "__main__":
#       ...
#       init_tool_registry()
#       httpd.serve_forever()


# ============================================================================
# CHANGE 3: Create new version of _execute_process_expert_intent (OPTIONAL)
# ============================================================================

# OPTION A: Replace the entire function with registry version

def _execute_process_expert_intent_v2(
    intent: str, params: Dict[str, Any], session_id: str = ""
) -> Dict[str, Any]:
    """
    REFACTORED: Execute process expert intent using ToolRegistry.

    Replaces the old hardcoded if-elif version that was ~215 lines.
    Now all tool routing and execution is delegated to ToolRegistry.

    Args:
        intent: Tool intent name (e.g., "design_process", "publish_draft")
        params: Tool parameters
        session_id: Session ID for this execution

    Returns:
        Tool execution result
    """
    try:
        # Execute through registry
        result = execute_tool_via_registry(intent, params, session_id=session_id)

        # Ensure "intent" field is in response for backward compatibility
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


# OPTION B: Keep old function name with wrapper (safer migration)

# At the end of the file, REPLACE the old function definition with:
_execute_process_expert_intent_OLD = _execute_process_expert_intent  # Backup


def _execute_process_expert_intent(
    intent: str, params: Dict[str, Any], session_id: str = ""
) -> Dict[str, Any]:
    """
    Execute process expert intent.

    Now uses ToolRegistry instead of hardcoded if-elif.
    Maintains backward compatibility with old response format.
    """
    return _execute_process_expert_intent_v2(intent, params, session_id)


# ============================================================================
# CHANGE 4: Update _run_process_expert_chat_turn (PARTIAL REFACTORING)
# ============================================================================

# REPLACE the tool execution section (around line 405-450) with:

# BEFORE (lines 404-450, complex logic with confirmation):
#   if intent in write_intents and not execute:
#       # Create structured confirmation record
#       expires_at = ...
#       confirmation_id = runtime_store.create_confirmation_record(...)
#       ...
#       operation_scripts = _build_operation_scripts(intent, params, parsed)
#       ...
#       return {..., "pending_confirmation": True, ...}
#   else:
#       tool_result = _execute_process_expert_intent(intent, params)

# AFTER (simplified, uses registry):
#   if intent in write_intents and not execute:
#       # Create structured confirmation record
#       expires_at = ...
#       confirmation_id = runtime_store.create_confirmation_record(...)
#       ...
#       return {..., "pending_confirmation": True, ...}
#   else:
#       tool_result = _execute_process_expert_intent(intent, params, session_id)


# ============================================================================
# CHANGE 5: Update confirmation response handler (line ~410-420)
# ============================================================================

# When user confirms, execute tool:

# OLD (line ~279):
#   tool_result = _execute_process_expert_intent(pending["intent"], pending["params"])

# NEW:
#   tool_result = _execute_process_expert_intent(
#       pending["intent"],
#       pending["params"],
#       session_id=session_id
#   )


# ============================================================================
# CHANGE 6: Create SessionState integration (OPTIONAL but RECOMMENDED)
# ============================================================================

# ADD helper functions:

def get_or_create_session_state(session_id: str) -> "SessionState":
    """Get or create SessionState for a session"""
    from tools.agent_framework import SessionState, ChatState

    if session_id not in session_states:
        session_states[session_id] = SessionState(session_id=session_id)

    return session_states[session_id]


def update_session_from_tool_result(
    session_id: str, intent: str, tool_result: Dict[str, Any]
) -> None:
    """Update session state based on tool execution result"""
    from tools.agent_framework import ChatState

    session_state = get_or_create_session_state(session_id)

    # Update based on result status
    status = tool_result.get("status", "unknown")

    if status == "ok":
        msg = f"执行了 {intent} 操作"
        session_state.add_message("system", msg)
        session_state.transition_to(ChatState.NORMAL)

    elif status in ["error", "validation_error"]:
        error_msg = tool_result.get("error") or tool_result.get("errors")
        session_state.add_message("system", f"错误: {error_msg}")
        session_state.transition_to(ChatState.ERROR)


# ADD global state tracking (line ~50):
session_states = {}  # session_id -> SessionState


# ============================================================================
# CHANGE 7: Remove old tool helper functions (CLEANUP)
# ============================================================================

# REMOVE these functions (they are no longer needed):

# - _create_design_draft() - functionality moved to DesignProcessTool
# - _publish_draft() - functionality moved to PublishDraftTool
# - _find_process_definition() - used by ModifyProcessTool
# - _build_operation_scripts() - can be kept if still used elsewhere

# KEEP these functions:
# - _now_iso() - utility function
# - _is_confirmation_message() - used for confirmation matching
# - _extract_json_dict() - used for LLM response parsing


# ============================================================================
# COMPLETE EXAMPLE: Refactored _run_process_expert_chat_turn
# ============================================================================

"""
def _run_process_expert_chat_turn(session_id: str, user_message: str) -> Dict[str, Any]:
    # [Keep existing message history and LLM parsing code ~line 267-357]
    history = process_chat_sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": user_message})

    # [... existing code for LLM parsing and validation ...]

    # NEW: Use SessionState
    session_state = get_or_create_session_state(session_id)
    session_state.add_message("user", user_message)

    # [Keep confirmation check logic ~line 271-299]
    pending = process_chat_pending_ops.get(session_id)
    if pending and _is_confirmation_message(user_message):
        # Execute confirmed tool
        tool_result = _execute_process_expert_intent(
            pending["intent"],
            pending["params"],
            session_id=session_id  # NEW: pass session_id
        )
        # ... rest of confirmation handling ...
        update_session_from_tool_result(session_id, pending["intent"], tool_result)

    # [Keep LLM parsing code ~line 301-357]
    recent = history[-8:]
    # ... rest of LLM parsing ...

    # REFACTORED: Use ToolRegistry for tool execution
    if intent in {"design_process", "modify_process"}:
        # These tools generate drafts instead of immediate execution
        tool_result = _execute_process_expert_intent(intent, params, session_id)

    elif intent in write_intents and not execute:
        # Create confirmation record (keep existing logic)
        confirmation_id = runtime_store.create_confirmation_record(...)
        # ... confirmation logic ...
        return {..., "pending_confirmation": True, ...}

    else:
        # Execute tool through registry
        tool_result = _execute_process_expert_intent(intent, params, session_id)

    # Update session state
    update_session_from_tool_result(session_id, intent, tool_result)

    # Return response (keep existing format)
    return {..., "tool_result": tool_result, ...}
"""


# ============================================================================
# TESTING THE REFACTORED CODE
# ============================================================================

"""
After applying changes, run these tests:

1. Existing HTTP Tests (Backward Compatibility)
   pytest tests/test_agent_adapters.py -v

2. New ToolRegistry Tests
   python3 tests/test_phase2_tools.py
   python3 tests/test_phase3_registry_integration.py

3. Integration Tests
   python3 -c "
       from tools.registry_manager import execute_tool
       result = execute_tool('design_process', {
           'requirement': '设计一个测试工艺'
       })
       assert result['status'] == 'validation_error'  # Too short
       print('✓ Tool execution works')
   "

4. Manual E2E Test
   Start server: python3 tools/agent_server.py
   Send request:
   curl -X POST http://localhost:8080/api/v1/process/expert/chat \\
     -H "Content-Type: application/json" \\
     -d '{
       "session_id": "test_123",
       "user_message": "设计一个地址治理工艺流程..."
     }'
"""


# ============================================================================
# MIGRATION SAFETY CHECKLIST
# ============================================================================

"""
Before going live with refactored code:

SAFETY CHECKS:
  ☐ All 9 tools are registered in ToolRegistry
  ☐ All tests pass (Phase 2 + Phase 3 + existing tests)
  ☐ Response format unchanged (backward compatible)
  ☐ All existing API endpoints work
  ☐ Session state transitions work correctly
  ☐ Confirmation workflow still works
  ☐ Error handling works for all scenarios
  ☐ Performance is not degraded

ROLLBACK PLAN:
  ☐ Keep old _execute_process_expert_intent_OLD as fallback
  ☐ Have git branch ready to revert if needed
  ☐ Monitor logs for new errors during rollout
  ☐ Have database snapshots before migration

MONITORING:
  ☐ Log all tool execution failures
  ☐ Track execution times for performance
  ☐ Alert on new error types
  ☐ Monitor API response codes
"""

print(__doc__)
