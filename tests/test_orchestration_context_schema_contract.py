from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_orchestration_context_schema_and_example_registered() -> None:
    root = Path(__file__).resolve().parents[1]
    base = root / "workpackage_schema"
    registry = json.loads((base / "registry.json").read_text(encoding="utf-8"))

    companion = (((registry.get("versions") or {}).get("v1") or {}).get("companion_artifacts") or {})
    schema_rel = str(companion.get("orchestration_context_schema") or "")
    sample_rel = str(companion.get("orchestration_context_example") or "")

    assert schema_rel == "schemas/v1/orchestration_context.v1.schema.json"
    assert sample_rel == "examples/v1/nanobot_orchestration_memory.v1.json"
    assert (base / schema_rel).exists()
    assert (base / sample_rel).exists()


def test_orchestration_context_example_validates_against_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    base = root / "workpackage_schema"
    schema = json.loads((base / "schemas" / "v1" / "orchestration_context.v1.schema.json").read_text(encoding="utf-8"))
    sample = json.loads((base / "examples" / "v1" / "nanobot_orchestration_memory.v1.json").read_text(encoding="utf-8"))

    errors = sorted(Draft202012Validator(schema).iter_errors(sample), key=lambda e: list(e.path))
    assert not errors


def test_orchestration_context_schema_required_keys() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "workpackage_schema" / "schemas" / "v1" / "orchestration_context.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    required = schema.get("required") or []
    for key in (
        "boot_context",
        "discovery_facts",
        "capability_snapshot",
        "blueprint_attempts",
        "opencode_task_ticket",
        "build_artifacts_index",
        "blocker_ticket",
        "gate_state",
        "runtime_evidence",
        "publish_decision",
        "timeline",
    ):
        assert key in required
