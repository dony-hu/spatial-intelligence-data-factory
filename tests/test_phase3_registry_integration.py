"""
Phase 3 Integration Tests - ToolRegistry and agent_server.py integration

Tests the ToolRegistry manager, tool registration, and execution.
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_dependencies():
    """Create mock objects for tool dependencies"""
    mock_runtime_store = Mock()
    mock_runtime_store.find_process_definition = Mock(return_value=None)
    mock_runtime_store.get_process_draft = Mock(return_value=None)
    mock_runtime_store.upsert_process_draft = Mock(
        return_value={"draft_id": "draft_123", "updated_at": "2026-02-13T10:00:00"}
    )

    mock_process_compiler = Mock()
    mock_process_compiler.compile = Mock(
        return_value=Mock(
            success=True,
            process_code="TEST_001",
            process_spec={},
            tool_scripts={},
            tool_metadata={},
            execution_readiness=100,
            validation_errors=[],
            validation_warnings=[],
        )
    )

    mock_process_db_api = Mock()
    mock_process_db_api.execute = Mock(return_value={"status": "ok"})

    return {
        "runtime_store": mock_runtime_store,
        "process_compiler": mock_process_compiler,
        "process_db_api": mock_process_db_api,
    }


def test_registry_initialization():
    """Test ToolRegistry initialization"""
    print("\n" + "=" * 70)
    print("Test: ToolRegistry Initialization")
    print("=" * 70)

    try:
        from tools.registry_manager import ToolRegistryManager

        # Reset any previous instance
        ToolRegistryManager.reset()

        # Create mock dependencies
        mocks = create_mock_dependencies()

        # Initialize registry
        registry = ToolRegistryManager.initialize(**mocks)

        assert registry is not None, "Registry should not be None"
        assert len(registry.tools) == 9, f"Expected 9 tools, got {len(registry.tools)}"

        print(f"✓ Registry initialized with {len(registry.tools)} tools")

        # Check all expected tools are registered
        expected_tools = {
            "design_process",
            "modify_process",
            "publish_draft",
            "create_process",
            "create_version",
            "query_process",
            "query_version",
            "query_process_tasks",
            "query_task_io",
        }

        registered_intents = set(registry.list_intents().keys())
        assert expected_tools == registered_intents, (
            f"Intent mismatch. Expected {expected_tools}, got {registered_intents}"
        )

        print(f"✓ All expected tools registered: {expected_tools}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tool_execution_via_registry():
    """Test executing tools through the registry"""
    print("\n" + "=" * 70)
    print("Test: Tool Execution via Registry")
    print("=" * 70)

    try:
        from tools.registry_manager import ToolRegistryManager, execute_tool

        # Reset and initialize
        ToolRegistryManager.reset()
        mocks = create_mock_dependencies()
        ToolRegistryManager.initialize(**mocks)

        # Test 1: Valid design_process execution
        print("\n  Subtest 1: Execute design_process with valid parameters")
        result = execute_tool(
            "design_process",
            {"requirement": "设计一个地址治理工艺流程，包括地址标准化和验证步骤"},
            session_id="test_session_001",
        )

        assert result["status"] == "ok", f"Expected status=ok, got {result['status']}"
        assert "result" in result or "error" not in result, "Result should be present on success"
        print(f"  ✓ design_process executed successfully")

        # Test 2: Validation error
        print("\n  Subtest 2: Execute with validation error")
        result = execute_tool(
            "design_process", {"requirement": "short"}, session_id="test_session_001"
        )

        assert result["status"] == "validation_error", (
            f"Expected validation_error, got {result['status']}"
        )
        assert (
            result["validation_errors"]
        ), "Validation errors should be present"
        print(f"  ✓ Validation error detected: {result['validation_errors']}")

        # Test 3: Unknown intent
        print("\n  Subtest 3: Execute unknown intent")
        result = execute_tool(
            "unknown_intent", {"param": "value"}, session_id="test_session_001"
        )

        assert result["status"] == "error", f"Expected error, got {result['status']}"
        assert "未知的意图" in result.get("error", ""), "Should mention unknown intent"
        print(f"  ✓ Unknown intent rejected: {result['error']}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test backward compatibility with old API format"""
    print("\n" + "=" * 70)
    print("Test: Backward Compatibility with Old API Format")
    print("=" * 70)

    try:
        from tools.registry_manager import ToolRegistryManager, execute_tool

        # Reset and initialize
        ToolRegistryManager.reset()
        mocks = create_mock_dependencies()
        ToolRegistryManager.initialize(**mocks)

        # Execute a tool and verify response format
        result = execute_tool(
            "query_process", {"code": "TEST_001"}, session_id="test_session_001"
        )

        # Check response structure (should match old format)
        required_fields = ["status", "tool_name"]
        missing_fields = [f for f in required_fields if f not in result]
        assert not missing_fields, f"Missing response fields: {missing_fields}"

        print(f"✓ Response format compatible: {list(result.keys())}")

        # Verify status values are recognizable
        valid_statuses = ["ok", "error", "validation_error"]
        assert result["status"] in valid_statuses, (
            f"Status {result['status']} not in {valid_statuses}"
        )

        print(f"✓ Response status valid: {result['status']}")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_registry_singleton():
    """Test ToolRegistry singleton behavior"""
    print("\n" + "=" * 70)
    print("Test: ToolRegistry Singleton Pattern")
    print("=" * 70)

    try:
        from tools.registry_manager import ToolRegistryManager

        # Reset
        ToolRegistryManager.reset()

        # Initialize first instance
        mocks = create_mock_dependencies()
        registry1 = ToolRegistryManager.initialize(**mocks)

        # Try to initialize again (should return same instance)
        registry2 = ToolRegistryManager.initialize(**mocks)

        assert registry1 is registry2, "Should return same instance on second initialize"
        print("✓ Singleton pattern verified: returns same instance")

        # Verify getting registry returns same instance
        registry3 = ToolRegistryManager.get_registry()
        assert registry1 is registry3, "get_registry() should return same instance"
        print("✓ get_registry() returns same instance")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_all_tools_registered():
    """Test that all 9 tools are properly registered"""
    print("\n" + "=" * 70)
    print("Test: All 9 Tools Registered")
    print("=" * 70)

    try:
        from tools.registry_manager import ToolRegistryManager

        # Reset and initialize
        ToolRegistryManager.reset()
        mocks = create_mock_dependencies()
        registry = ToolRegistryManager.initialize(**mocks)

        # Get all tools
        tools = registry.list_tools()
        intents = registry.list_intents()

        print(f"\nRegistered Tools ({len(tools)}):")
        for tool_name, description in sorted(tools.items()):
            print(f"  • {tool_name}: {description[:60]}...")

        print(f"\nRegistered Intents ({len(intents)}):")
        for intent, tool_name in sorted(intents.items()):
            print(f"  • {intent} → {tool_name}")

        # Verify counts
        assert len(tools) == 9, f"Expected 9 tools, got {len(tools)}"
        assert len(intents) == 9, f"Expected 9 intents, got {len(intents)}"

        print(f"\n✓ All 9 tools registered")
        print(f"✓ All 9 intents mapped")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║              Phase 3: ToolRegistry Integration Tests              ║")
    print("║                   Testing Registry Manager                         ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    tests = [
        ("Registry Initialization", test_registry_initialization),
        ("Tool Execution via Registry", test_tool_execution_via_registry),
        ("Backward Compatibility", test_backward_compatibility),
        ("Registry Singleton", test_registry_singleton),
        ("All Tools Registered", test_all_tools_registered),
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
    print("Phase 3 Integration Test Summary")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {test_name}: {status}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n✓ All Phase 3 integration tests PASSED")
    else:
        print(f"\n✗ {total_count - passed_count} Phase 3 integration test(s) FAILED")

    print("=" * 70)
