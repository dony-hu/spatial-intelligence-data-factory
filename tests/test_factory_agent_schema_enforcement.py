from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from packages.factory_agent.agent import FactoryAgent


def _load_v1_schema() -> dict:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "workpackage_schema" / "schemas" / "v1" / "workpackage_schema.v1.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_factory_agent_generate_workpackage_blueprint_is_schema_v1_valid(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-for-unit")
    monkeypatch.setenv("WORKPACKAGE_BLUEPRINT_MAX_ROUNDS", "1")
    schema = _load_v1_schema()
    validator = Draft202012Validator(schema)
    agent = FactoryAgent()

    # Minimal LLM output, the agent should enrich/fix it to full schema.
    monkeypatch.setattr(
        agent,
        "_run_workpackage_blueprint_query",
        lambda *_args, **_kwargs: {
            "status": "ok",
            "answer": json.dumps(
                {
                    "workpackage": {
                        "name": "schema-enforce",
                        "version": "v1.0.0",
                        "objective": "地址治理",
                    }
                },
                ensure_ascii=False,
            ),
        },
    )

    result = agent.converse("请创建地址治理工作包 schema-enforce-v1.0.0")
    assert result["status"] == "ok"
    blueprint = result.get("workpackage_blueprint") or {}
    errors = sorted(validator.iter_errors(blueprint), key=lambda e: list(e.path))
    assert not errors, [f"{'/'.join(str(x) for x in err.path)}: {err.message}" for err in errors]


def test_factory_agent_written_workpackage_json_is_schema_v1_valid(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-for-unit")
    monkeypatch.setenv("WORKPACKAGE_BLUEPRINT_MAX_ROUNDS", "1")
    schema = _load_v1_schema()
    validator = Draft202012Validator(schema)
    agent = FactoryAgent()

    monkeypatch.setattr(
        agent,
        "_run_workpackage_blueprint_query",
        lambda *_args, **_kwargs: {
            "status": "ok",
            "answer": json.dumps(
                {
                    "workpackage": {
                        "name": "schema-write",
                        "version": "v1.0.0",
                        "objective": "地址标准化与验真",
                    }
                },
                ensure_ascii=False,
            ),
        },
    )

    out = agent.converse("创建工作包 schema-write-v1.0.0")
    assert out["status"] == "ok"
    bundle_path = Path(str(out.get("bundle_path") or ""))
    payload = json.loads((bundle_path / "workpackage.json").read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    assert not errors, [f"{'/'.join(str(x) for x in err.path)}: {err.message}" for err in errors]
