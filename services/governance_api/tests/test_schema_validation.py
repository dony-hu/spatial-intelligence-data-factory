import json
from pathlib import Path


def test_schema_files_exist_and_have_required_keys() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "schemas"
    input_schema = json.loads((root / "address_input.schema.json").read_text(encoding="utf-8"))
    output_schema = json.loads((root / "address_output.schema.json").read_text(encoding="utf-8"))

    assert "required" in input_schema
    assert "records" in input_schema["properties"]
    assert "results" in output_schema["properties"]
