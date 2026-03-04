from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_workpackage_schema_address_case_example_exists_and_parseable() -> None:
    root = Path(__file__).resolve().parents[1]
    sample_path = root / "workpackage_schema" / "examples" / "v1" / "address_batch_governance.workpackage_schema.v1.json"
    assert sample_path.exists(), "地址治理案例样例缺失"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    assert payload.get("schema_version") == "workpackage_schema.v1"
    assert payload.get("mode") == "blueprint_mode"
    io_contract = payload.get("io_contract") if isinstance(payload.get("io_contract"), dict) else {}
    assert isinstance(io_contract.get("input_schema"), dict)
    assert isinstance(io_contract.get("output_schema"), dict)


def test_workpackage_schema_address_case_example_validates_against_v1_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    base = root / "workpackage_schema"
    registry = json.loads((base / "registry.json").read_text(encoding="utf-8"))
    schema_rel = str((((registry.get("versions") or {}).get("v1") or {}).get("schema_file") or ""))
    schema = json.loads((base / schema_rel).read_text(encoding="utf-8"))
    sample = json.loads((base / "examples" / "v1" / "address_batch_governance.workpackage_schema.v1.json").read_text(encoding="utf-8"))

    errors = sorted(Draft202012Validator(schema).iter_errors(sample), key=lambda e: list(e.path))
    assert not errors, "address_batch_governance 示例不符合 v1 schema"


def test_workpackage_schema_address_case_example_enforces_no_fallback() -> None:
    root = Path(__file__).resolve().parents[1]
    sample = json.loads(
        (
            root
            / "workpackage_schema"
            / "examples"
            / "v1"
            / "address_batch_governance.workpackage_schema.v1.json"
        ).read_text(encoding="utf-8")
    )
    failure_handling = (((sample.get("execution_plan") or {}).get("failure_handling") or {}))
    assert failure_handling.get("on_api_failure") == "block_error_no_fallback"


def test_workpackage_schema_address_case_example_includes_skills() -> None:
    root = Path(__file__).resolve().parents[1]
    sample = json.loads(
        (root / "workpackage_schema" / "examples" / "v1" / "address_batch_governance.workpackage_schema.v1.json").read_text(
            encoding="utf-8"
        )
    )
    skills = sample.get("skills")
    assert isinstance(skills, list) and skills, "sample 必须包含 skills 列表"
