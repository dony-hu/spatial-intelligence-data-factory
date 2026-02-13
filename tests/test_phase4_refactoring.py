"""
Phase 4: Final Integration Tests - Complete Validation

Tests the refactored agent_server.py with ToolRegistry integration
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all refactored imports work correctly"""
    print("\n" + "=" * 70)
    print("Test 1: Refactored Imports")
    print("=" * 70)

    try:
        from tools.agent_server import (
            init_tool_registry,
            get_or_create_session_state,
            update_session_from_tool_result,
            _execute_process_expert_intent,
        )
        print("✓ All refactored functions imported successfully")

        from tools.registry_manager import execute_tool
        print("✓ ToolRegistry functions imported successfully")

        from tools.agent_framework import SessionState, ChatState
        print("✓ Agent framework classes imported successfully")

        return True

    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_registry_initialization():
    """Test ToolRegistry initialization through agent_server"""
    print("\n" + "=" * 70)
    print("Test 2: ToolRegistry Initialization")
    print("=" * 70)

    try:
        from tools.agent_server import init_tool_registry, registry_initialized, tool_registry

        # Initialize
        init_tool_registry()

        print("✓ ToolRegistry initialized successfully")

        # Verify it's initialized
        from tools.agent_server import registry_initialized as reg_init
        if not reg_init:
            print("✗ Registry not properly initialized")
            return False

        print("✓ Registry initialization flag set correctly")
        return True

    except Exception as e:
        print(f"✗ Registry initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_state_integration():
    """Test SessionState integration"""
    print("\n" + "=" * 70)
    print("Test 3: SessionState Integration")
    print("=" * 70)

    try:
        from tools.agent_server import (
            get_or_create_session_state,
            update_session_from_tool_result,
            session_states,
        )
        from tools.agent_framework import ChatState

        # Create session state
        session_id = "test_session_001"
        state = get_or_create_session_state(session_id)

        assert state is not None, "Session state should not be None"
        assert state.session_id == session_id, "Session ID mismatch"
        assert state.current_state == ChatState.NORMAL, "Initial state should be NORMAL"
        print("✓ SessionState created and initialized correctly")

        # Test update with success
        tool_result = {"status": "ok", "result": {"test": "data"}}
        update_session_from_tool_result(session_id, "test_intent", tool_result)

        assert state.current_state == ChatState.NORMAL, "Should remain NORMAL after successful execution"
        print("✓ SessionState updated correctly on success")

        # Test update with error
        tool_result_error = {"status": "error", "error": "Test error"}
        update_session_from_tool_result(session_id, "test_intent", tool_result_error)

        assert state.current_state == ChatState.ERROR, "Should transition to ERROR on error"
        print("✓ SessionState updated correctly on error")

        return True

    except Exception as e:
        print(f"✗ SessionState integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_execution():
    """Test tool execution through refactored agent_server"""
    print("\n" + "=" * 70)
    print("Test 4: Tool Execution Through Refactored Function")
    print("=" * 70)

    try:
        from tools.agent_server import _execute_process_expert_intent, init_tool_registry

        # Initialize registry first
        init_tool_registry()

        # Test 1: Valid tool execution
        result = _execute_process_expert_intent("query_process", {}, session_id="test_001")
        assert result is not None, "Result should not be None"
        assert "intent" in result, "Intent should be in result"
        print("✓ Tool execution returns expected format")

        # Test 2: Response has intent field (backward compatibility)
        assert result["intent"] == "query_process", "Intent field should match"
        print("✓ Backward compatibility maintained (intent field present)")

        # Test 3: Error handling for invalid tool
        result_invalid = _execute_process_expert_intent("invalid_tool_xyz", {})
        assert result_invalid["status"] == "error", "Invalid tool should return error"
        assert "intent" in result_invalid, "Intent should be in error response too"
        print("✓ Invalid tool rejection working correctly")

        # Test 4: Validation error handling
        result_validation = _execute_process_expert_intent(
            "design_process",
            {"requirement": "short"},  # Too short
            session_id="test_002"
        )
        assert result_validation["status"] == "validation_error", "Should validate parameters"
        print("✓ Parameter validation working correctly")

        return True

    except Exception as e:
        print(f"✗ Tool execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test that refactored code maintains backward compatibility"""
    print("\n" + "=" * 70)
    print("Test 5: Backward Compatibility")
    print("=" * 70)

    try:
        from tools.agent_server import _execute_process_expert_intent, init_tool_registry

        init_tool_registry()

        # Test response format is compatible
        result = _execute_process_expert_intent("query_process", {})

        required_fields = ["status", "intent"]
        missing = [f for f in required_fields if f not in result]
        assert not missing, f"Missing required fields: {missing}"
        print("✓ Response format is backward compatible")

        # Test status values are recognized
        valid_statuses = ["ok", "error", "validation_error", "pending_confirmation"]
        assert result.get("status") in valid_statuses, f"Unknown status: {result.get('status')}"
        print("✓ Response status values are valid")

        return True

    except Exception as e:
        print(f"✗ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """Test that refactored code has acceptable performance"""
    print("\n" + "=" * 70)
    print("Test 6: Performance")
    print("=" * 70)

    try:
        from tools.agent_server import _execute_process_expert_intent, init_tool_registry

        init_tool_registry()

        # Warm up
        for _ in range(3):
            _execute_process_expert_intent("query_process", {})

        # Benchmark
        iterations = 50
        t0 = time.time()
        for _ in range(iterations):
            _execute_process_expert_intent("query_process", {})
        elapsed = time.time() - t0

        avg_ms = (elapsed / iterations) * 1000
        print(f"Average execution time: {avg_ms:.2f}ms ({iterations} iterations)")

        # Performance should be acceptable (< 100ms per call)
        assert avg_ms < 100, f"Performance degradation: {avg_ms}ms"
        print(f"✓ Performance test passed (target: <100ms, actual: {avg_ms:.2f}ms)")

        return True

    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║          Phase 4: Final Integration Test Suite                    ║")
    print("║            Testing Refactored agent_server.py                     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    tests = [
        ("Refactored Imports", test_imports),
        ("ToolRegistry Initialization", test_registry_initialization),
        ("SessionState Integration", test_session_state_integration),
        ("Tool Execution", test_tool_execution),
        ("Backward Compatibility", test_backward_compatibility),
        ("Performance", test_performance),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Phase 4 Test Summary")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {test_name}: {status}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n✓ All Phase 4 tests PASSED - Refactoring successful!")
    else:
        print(f"\n✗ {total_count - passed_count} Phase 4 test(s) FAILED")

    print("=" * 70)

    sys.exit(0 if passed_count == total_count else 1)
