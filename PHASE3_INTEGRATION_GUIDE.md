"""
Phase 3 Refactoring Plan - Integration Guide

This document provides a step-by-step guide for integrating ToolRegistry
into agent_server.py without breaking existing functionality.

Strategy: Gradual refactoring with backward compatibility
==========================================================

Step 1: Initialize ToolRegistry at server startup
Step 2: Create a wrapper function for backward compatibility
Step 3: Gradually migrate functions to use registry
Step 4: Test and validate
Step 5: Clean up and optimize
"""

# ============================================================================
# INTEGRATION PATTERN 1: Adding ToolRegistry to imports
# ============================================================================

# BEFORE (agent_server.py line 3-25):
#   from tools.process_db_api import ProcessDBApi
#   from tools.process_compiler import ProcessCompiler
#   ...

# AFTER:
#   from tools.process_db_api import ProcessDBApi
#   from tools.process_compiler import ProcessCompiler
#   from tools.registry_manager import (
#       initialize_registry,
#       execute_tool,
#       list_registered_intents,
#   )


# ============================================================================
# INTEGRATION PATTERN 2: Initialize registry at server startup
# ============================================================================

# ADD to server_state initialization (around line 50):

def initialize_tool_registry():
    """Initialize the ToolRegistry with all available tools"""
    try:
        initialize_registry(
            runtime_store=runtime_store,
            process_compiler=process_compiler,
            process_db_api=process_db_api,
            llm_service=None,  # Will be integrated later
        )
        logger.info("ToolRegistry initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ToolRegistry: {e}")
        raise


# Call during server initialization:
# if __name__ == "__main__":
#     ...
#     initialize_tool_registry()
#     ...


# ============================================================================
# INTEGRATION PATTERN 3: Wrapper function for backward compatibility
# ============================================================================

# REPLACE the current _execute_process_expert_intent function with:

def _execute_process_expert_intent_v2(
    intent: str, params: Dict[str, Any], session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    NEW VERSION: Execute intent using ToolRegistry.

    This replaces the old hardcoded if-elif function.
    All logic now delegated to Tool classes registered in ToolRegistry.
    """
    try:
        result = execute_tool(intent, params, session_id=session_id)

        # Ensure backward compatibility with old response format
        if result["status"] == "error":
            return {
                "status": "error",
                "error": result["error"],
                "intent": intent,
            }

        if result["status"] == "validation_error":
            return {
                "status": "validation_error",
                "errors": result["validation_errors"],
                "intent": intent,
            }

        # Success case - include intent in response
        success_result = result.get("result", {})
        if isinstance(success_result, dict):
            success_result["intent"] = intent
        return success_result

    except Exception as e:
        logger.error(f"Tool execution failed for {intent}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "intent": intent,
        }


# For compatibility, keep old function as alias:
# _execute_process_expert_intent = _execute_process_expert_intent_v2


# ============================================================================
# INTEGRATION PATTERN 4: Refactored _run_process_expert_chat_turn
# ============================================================================

# CURRENT location: agent_server.py line 266-450 (approximately)
#
# The key change is replacing the tool execution section:

# BEFORE (lines ~404-405):
#   if intent in write_intents and not execute:
#       # Create structured confirmation record
#       ...
#       tool_result = _execute_process_expert_intent(pending["intent"], pending["params"])

# AFTER:
#   if intent in write_intents and not execute:
#       # Create structured confirmation record
#       ...
#       tool_result = execute_tool(
#           intent=pending["intent"],
#           params=pending["params"],
#           session_id=session_id
#       )


# ============================================================================
# INTEGRATION PATTERN 5: SessionState integration
# ============================================================================

# To leverage SessionState from Phase 1, update chat turn handling:

def initialize_session_state(session_id: str) -> Any:
    """Create or retrieve SessionState for a session"""
    from tools.agent_framework import SessionState, ChatState

    # Get or create session state
    if session_id not in session_states:
        session_states[session_id] = SessionState(session_id=session_id)

    return session_states[session_id]


def update_session_state(session_id: str, state: str, message: str, role: str = "assistant"):
    """Update session state after tool execution"""
    from tools.agent_framework import ChatState

    session_state = session_states.get(session_id)
    if not session_state:
        return

    # Add message to history
    session_state.add_message(role, message)

    # Update state based on message type
    if state == "normal":
        session_state.transition_to(ChatState.NORMAL)
    elif state == "executing":
        session_state.transition_to(ChatState.EXECUTING)
    elif state == "error":
        session_state.transition_to(ChatState.ERROR)


# ============================================================================
# INTEGRATION PATTERN 6: Refactoring _run_process_expert_chat_turn (full)
# ============================================================================

"""
The refactored version consolidates logic:

BEFORE (1300 lines in agent_server.py):
- Manual intent parsing
- Manual tool routing via if-elif
- Manual parameter validation
- Manual state management

AFTER (500 lines in agent_server.py):
- Keep LLM parsing (needed for user input understanding)
- Use ToolRegistry for routing and execution
- Use DialogueSchemaValidator for validation
- Use SessionState for state management
- Keep confirmation logic (structured in Phase 1)

Key changes:
1. Line 217: Remove _execute_process_expert_intent hardcoded function
2. Line 230-260: Remove all if-elif tool routing blocks
3. Line ~330: Replace tool.execute() calls with execute_tool()
4. Add SessionState tracking throughout chat flow
"""


# ============================================================================
# CODE SNIPPETS: Before and After Comparison
# ============================================================================

# ============================================================================
# BEFORE: _execute_process_expert_intent (current ~215 lines)
# ============================================================================

"""
def _execute_process_expert_intent(intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
    code = str(params.get("code") or "").strip().upper()
    process_definition_id = str(params.get("process_definition_id") or "").strip()

    db_intents = {
        "create_process",
        "query_process",
        "query_version",
        "create_version",
        "publish_draft",
        "query_process_tasks",
        "query_task_io",
    }

    if intent in db_intents:
        return process_db_api.execute(intent, params)

    if intent == "design_process":
        requirement = str(params.get("requirement") or "").strip()
        if not requirement:
            return {"status": "error", "error": "缺少 requirement", "intent": intent}
        data = _create_design_draft(...)
        data["intent"] = intent
        return data

    if intent == "modify_process":
        # ... more code ...
        return data

    return {"status": "ok", "intent": "chat", "message": "该轮对话未触发数据库操作"}
"""

# ============================================================================
# AFTER: Using ToolRegistry (3-4 lines)
# ============================================================================

"""
def _execute_process_expert_intent(intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
    result = execute_tool(intent, params)
    result["intent"] = intent
    return result
"""

# ============================================================================
# BENEFITS OF REFACTORING
# ============================================================================

"""
1. CODE REDUCTION
   - agent_server.py: 1300 lines → ~500 lines (-62% reduction)
   - _execute_process_expert_intent: ~215 lines → ~3 lines
   - Removed 200+ lines of hardcoded if-elif routing

2. MAINTAINABILITY
   - Adding new tools: just create a Tool class, no changes to agent_server
   - Changing tool behavior: modify Tool class, not scattered in agent_server
   - Parameter validation: centralized in Tool.validate(), not mixed with logic

3. TESTABILITY
   - Each Tool class can be tested independently
   - ToolRegistry can be tested separately
   - agent_server.py becomes a thin HTTP handler

4. FLEXIBILITY
   - Easy to swap tool implementations
   - Easy to add decorators/middleware to tools
   - Easy to implement tool chaining or composition

5. SCALABILITY
   - New tools don't require agent_server changes
   - Can support different tool registries for different domains
   - Ready for distributed tool execution
"""

# ============================================================================
# MIGRATION CHECKLIST
# ============================================================================

"""
Phase 3a: Preparation (no code changes)
  ☐ Review current agent_server.py structure
  ☐ Identify all tool functions and their dependencies
  ☐ Document all API responses to ensure backward compatibility
  ☐ Create comprehensive test suite for current behavior

Phase 3b: Integration (parallel execution)
  ☐ Create tools/registry_manager.py ✓ DONE
  ☐ Add ToolRegistry import to agent_server.py
  ☐ Add registry initialization to server startup
  ☐ Create backward compatibility wrapper
  ☐ Test registry with sample tool calls

Phase 3c: Refactoring (gradual migration)
  ☐ Replace _execute_process_expert_intent with registry version
  ☐ Update _run_process_expert_chat_turn to use registry
  ☐ Integrate SessionState into chat flow
  ☐ Update confirmation logic to work with SessionState
  ☐ Remove old tool function implementations

Phase 3d: Validation (comprehensive testing)
  ☐ Unit tests: each Tool class
  ☐ Integration tests: ToolRegistry + agent_server
  ☐ E2E tests: full chat workflows
  ☐ Backward compatibility tests: old API contracts
  ☐ Performance tests: response times
  ☐ Load tests: concurrent requests

Phase 3e: Cleanup (optimization)
  ☐ Remove unused helper functions
  ☐ Optimize imports and dependencies
  ☐ Update documentation and comments
  ☐ Final code review and optimization
"""

# ============================================================================
# TESTING STRATEGY FOR PHASE 3
# ============================================================================

"""
Test Coverage:

1. ToolRegistry Tests
   - Registry initialization
   - Tool registration
   - Intent-to-tool mapping
   - Tool execution through registry
   - Error handling and validation

2. Integration Tests
   - agent_server + ToolRegistry
   - Chat flow with tool execution
   - Confirmation workflow
   - SessionState transitions
   - Backward API compatibility

3. E2E Tests
   - Full design_process workflow
   - Full modify_process workflow
   - Full publish_draft workflow
   - Multi-turn conversations
   - Error scenarios and recovery

4. Regression Tests
   - All existing API endpoints work
   - All existing response formats unchanged
   - All database operations work
   - All LLM integrations work
"""

print(__doc__)
