"""
Phase 2 Verification Tests - Test Tool class imports and basic functionality
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all Tool classes can be imported"""
    print("=" * 70)
    print("Phase 2 Tool Import Tests")
    print("=" * 70)

    try:
        from tools.agent_framework import BaseTool, ToolSchema
        print("✓ BaseTool and ToolSchema imported successfully")
    except Exception as e:
        print(f"✗ Failed to import BaseTool/ToolSchema: {e}")
        return False

    tools_to_import = [
        ("DesignProcessTool", "tools.process_tools"),
        ("ModifyProcessTool", "tools.process_tools"),
        ("CreateProcessTool", "tools.process_tools"),
        ("CreateProcessVersionTool", "tools.process_tools"),
        ("PublishDraftTool", "tools.process_tools"),
        ("QueryProcessTool", "tools.process_tools"),
        ("QueryProcessVersionTool", "tools.process_tools"),
        ("QueryProcessTasksTool", "tools.process_tools"),
        ("QueryTaskIOTool", "tools.process_tools"),
    ]

    all_imported = True
    for tool_name, module_path in tools_to_import:
        try:
            module = __import__(module_path, fromlist=[tool_name])
            tool_class = getattr(module, tool_name)
            print(f"✓ {tool_name} imported successfully")
        except Exception as e:
            print(f"✗ Failed to import {tool_name}: {e}")
            all_imported = False

    return all_imported


def test_instantiation():
    """Test that all Tool classes can be instantiated"""
    print("\n" + "=" * 70)
    print("Phase 2 Tool Instantiation Tests")
    print("=" * 70)

    from tools.process_tools import (
        DesignProcessTool, ModifyProcessTool, CreateProcessTool,
        CreateProcessVersionTool, PublishDraftTool,
        QueryProcessTool, QueryProcessVersionTool,
        QueryProcessTasksTool, QueryTaskIOTool
    )

    tools = [
        ("DesignProcessTool", DesignProcessTool),
        ("ModifyProcessTool", ModifyProcessTool),
        ("CreateProcessTool", CreateProcessTool),
        ("CreateProcessVersionTool", CreateProcessVersionTool),
        ("PublishDraftTool", PublishDraftTool),
        ("QueryProcessTool", QueryProcessTool),
        ("QueryProcessVersionTool", QueryProcessVersionTool),
        ("QueryProcessTasksTool", QueryProcessTasksTool),
        ("QueryTaskIOTool", QueryTaskIOTool),
    ]

    all_instantiated = True
    for tool_name, tool_class in tools:
        try:
            instance = tool_class()
            assert isinstance(instance, tool_class)
            assert hasattr(instance, "name")
            assert hasattr(instance, "description")
            assert hasattr(instance, "input_schema")
            assert hasattr(instance, "validate")
            assert hasattr(instance, "execute")
            print(f"✓ {tool_name} instantiated with all required attributes")
        except Exception as e:
            print(f"✗ Failed to instantiate {tool_name}: {e}")
            all_instantiated = False

    return all_instantiated


def test_tool_metadata():
    """Test tool metadata (name, description, schema)"""
    print("\n" + "=" * 70)
    print("Phase 2 Tool Metadata Tests")
    print("=" * 70)

    from tools.process_tools import (
        DesignProcessTool, ModifyProcessTool, CreateProcessTool,
        CreateProcessVersionTool, PublishDraftTool,
        QueryProcessTool, QueryProcessVersionTool,
        QueryProcessTasksTool, QueryTaskIOTool
    )

    tools = [
        DesignProcessTool(), ModifyProcessTool(), CreateProcessTool(),
        CreateProcessVersionTool(), PublishDraftTool(),
        QueryProcessTool(), QueryProcessVersionTool(),
        QueryProcessTasksTool(), QueryTaskIOTool()
    ]

    for tool in tools:
        print(f"\n  Tool: {tool.name}")
        print(f"    Description: {tool.description}")
        print(f"    Required params: {tool.input_schema.required}")
        print(f"    Total params: {len(tool.input_schema.properties)}")


def test_validation():
    """Test parameter validation for each tool"""
    print("\n" + "=" * 70)
    print("Phase 2 Tool Validation Tests")
    print("=" * 70)

    from tools.process_tools import DesignProcessTool, PublishDraftTool

    # Test DesignProcessTool validation
    tool = DesignProcessTool()
    print("\nDesignProcessTool Validation:")

    # Valid parameters
    is_valid, errors = tool.validate({
        "requirement": "设计一个地址治理工艺，需要验证地址的有效性"
    })
    print(f"  Valid requirement: {is_valid} (errors: {errors})")

    # Invalid parameters - missing required
    is_valid, errors = tool.validate({})
    print(f"  Missing requirement: {is_valid} (errors: {errors})")

    # Invalid parameters - too short
    is_valid, errors = tool.validate({"requirement": "short"})
    print(f"  Short requirement: {is_valid} (errors: {errors})")

    # Test PublishDraftTool validation
    tool = PublishDraftTool()
    print("\nPublishDraftTool Validation:")

    # Valid parameters
    is_valid, errors = tool.validate({
        "draft_id": "draft_abc123def456"
    })
    print(f"  Valid draft_id: {is_valid} (errors: {errors})")

    # Invalid parameters - missing required
    is_valid, errors = tool.validate({})
    print(f"  Missing draft_id: {is_valid} (errors: {errors})")

    # Invalid parameters - invalid format
    is_valid, errors = tool.validate({
        "draft_id": "invalid_format"
    })
    print(f"  Invalid draft_id format: {is_valid} (errors: {errors})")


def test_schema_format():
    """Test that ToolSchema follows JSON Schema format"""
    print("\n" + "=" * 70)
    print("Phase 2 Tool Schema Format Tests")
    print("=" * 70)

    from tools.process_tools import DesignProcessTool
    from tools.agent_framework import ToolSchema

    tool = DesignProcessTool()
    schema = tool.input_schema

    print(f"\nDesignProcessTool Schema:")
    print(f"  Type: {schema.type}")
    print(f"  Required fields: {schema.required}")
    print(f"  Properties:")
    for prop_name, prop_schema in schema.properties.items():
        print(f"    - {prop_name}: {prop_schema.get('type', 'N/A')}")
    print(f"  Additional Properties Allowed: {not getattr(schema, 'additionalProperties', True) == False}")


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║          Phase 2: Tool Class Implementation Verification          ║")
    print("║              Verifying 9 Standard Tool Classes                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    results = []
    results.append(("Imports", test_imports()))
    results.append(("Instantiation", test_instantiation()))
    test_tool_metadata()
    test_validation()
    test_schema_format()

    # Summary
    print("\n" + "=" * 70)
    print("Phase 2 Verification Summary")
    print("=" * 70)
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(passed for _, passed in results)
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All Phase 2 verification tests PASSED")
    else:
        print("✗ Some Phase 2 verification tests FAILED")
    print("=" * 70)
