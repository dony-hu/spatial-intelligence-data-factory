from __future__ import annotations

import json
from pathlib import Path

from packages.factory_agent.opencode_workpackage_builder import OpenCodeWorkpackageBuilder


def test_opencode_workpackage_builder_generates_bundle_from_plan_only(tmp_path: Path) -> None:
    builder = OpenCodeWorkpackageBuilder()
    bundle_dir = tmp_path / "wp-demo-v1.0.0"
    blueprint = {
        "workpackage": {"name": "wp-demo", "version": "v1.0.0", "objective": "demo"},
        "api_plan": {
            "missing_apis": [
                {
                    "name": "ext_api_a",
                    "endpoint": "https://example.com/a",
                    "requires_key": True,
                    "api_key_env": "EXT_API_A_KEY",
                }
            ]
        },
        "scripts": [
            {
                "name": "run_pipeline.py",
                "purpose": "run",
                "runtime": "python",
                "entry": "python scripts/run_pipeline.py",
                "content": "print('llm_payload_should_not_execute')",
            }
        ],
    }
    builder.build_bundle(bundle_dir=bundle_dir, blueprint=blueprint, sources=["fengtu"])

    run_script = (bundle_dir / "scripts" / "run_pipeline.py").read_text(encoding="utf-8")
    assert "generated_by = \"opencode_agent\"" in run_script
    assert "llm_payload_should_not_execute" not in run_script

    entrypoint_py = (bundle_dir / "entrypoint.py").read_text(encoding="utf-8")
    assert "subprocess.run" in entrypoint_py
    assert "exec(" not in entrypoint_py

    env_example = (bundle_dir / "config" / "provider_keys.env.example").read_text(encoding="utf-8")
    assert "EXT_API_A_KEY=" in env_example

    build_report = json.loads((bundle_dir / "observability" / "opencode_build_report.json").read_text(encoding="utf-8"))
    assert build_report.get("status") == "success"
    assert str(build_report.get("bundle_name") or "") == "wp-demo-v1.0.0"

    payload = json.loads((bundle_dir / "workpackage.json").read_text(encoding="utf-8"))
    assert payload.get("name") is None
    assert str(((payload.get("workpackage") or {}).get("name")) or "") == "wp-demo"
