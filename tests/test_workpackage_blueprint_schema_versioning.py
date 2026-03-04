from __future__ import annotations

import json
from pathlib import Path


def test_workpackage_schema_registry_and_v1_file() -> None:
    root = Path(__file__).resolve().parents[1]
    registry_path = root / "workpackage_schema" / "registry.json"
    assert registry_path.exists(), "registry.json 缺失"

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    schema_rel = str((((registry.get("versions") or {}).get("v1") or {}).get("schema_file") or ""))
    schema_v1_path = root / "workpackage_schema" / schema_rel
    assert schema_v1_path.exists(), "v1 schema 缺失"
    schema_v1 = json.loads(schema_v1_path.read_text(encoding="utf-8"))

    assert registry.get("current_version") == "v1"
    versions = registry.get("versions")
    assert isinstance(versions, dict)
    assert versions.get("v1", {}).get("schema_file") == "schemas/v1/workpackage_schema.v1.schema.json"

    assert schema_v1.get("type") == "object"
    required = schema_v1.get("required")
    assert isinstance(required, list)
    for field in [
        "schema_version",
        "mode",
        "workpackage",
        "architecture_context",
        "io_contract",
        "api_plan",
        "execution_plan",
        "scripts",
        "skills",
    ]:
        assert field in required

    properties = schema_v1.get("properties")
    assert isinstance(properties, dict)
    assert properties.get("schema_version", {}).get("const") == "workpackage_schema.v1"
    assert properties.get("mode", {}).get("enum") == ["blueprint_mode"]
