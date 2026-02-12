#!/usr/bin/env python3
"""Validate all schema examples under schemas/agent/examples."""

import json
from pathlib import Path
import sys


def main() -> int:
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        print("ERROR: jsonschema is not installed. Run: pip install jsonschema")
        return 2

    root = Path(__file__).resolve().parent.parent
    schema_dir = root / "schemas" / "agent"
    example_dir = schema_dir / "examples"

    mapping = {
        "task-spec.sample.json": "TaskSpec.json",
        "plan.sample.json": "Plan.json",
        "changeset.sample.json": "ChangeSet.json",
        "approval-pack.sample.json": "ApprovalPack.json",
        "evidence.sample.json": "Evidence.json",
        "eval-report.sample.json": "EvalReport.json",
    }

    failed = False
    for sample, schema_file in mapping.items():
        schema = json.loads((schema_dir / schema_file).read_text(encoding="utf-8"))
        instance = json.loads((example_dir / sample).read_text(encoding="utf-8"))

        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
        if errors:
            failed = True
            print(f"FAIL: {sample} against {schema_file}")
            for e in errors:
                path = ".".join(str(x) for x in e.path) or "<root>"
                print(f"  - {path}: {e.message}")
        else:
            print(f"PASS: {sample} against {schema_file}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
