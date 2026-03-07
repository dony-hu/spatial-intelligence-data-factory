from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app


def test_runtime_workpackage_blueprint_api_contract() -> None:
    client = TestClient(app)
    workpackage_id = "wp_blueprint_001"
    version = "v1.0.0"
    bundle_name = f"{workpackage_id}-{version}"
    bundle_dir = Path("workpackages/bundles") / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    try:
        (bundle_dir / "workpackage.json").write_text(
            json.dumps(
                {
                    "name": workpackage_id,
                    "version": version,
                    "sources": ["fengtu", "opencagedata"],
                    "target": "地址标准化+验真+空间图谱",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        resp = client.get(
            "/v1/governance/observability/runtime/workpackage-blueprint"
            f"?workpackage_id={workpackage_id}&version={version}"
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("workpackage_id") == workpackage_id
        assert payload.get("version") == version
        assert isinstance(payload.get("workpackage_config"), dict)
        assert "publish_record" in payload
        assert isinstance(payload.get("registered_apis"), list)
        assert any(str(item.get("name") or "").strip() == "地址标准化" for item in payload.get("registered_apis") or [])
    finally:
        shutil.rmtree(bundle_dir, ignore_errors=True)


def test_runtime_workpackage_blueprint_api_uses_api_plan_sources_when_sources_missing() -> None:
    client = TestClient(app)
    workpackage_id = "wp_blueprint_api_plan_001"
    version = "v1.0.0"
    bundle_name = f"{workpackage_id}-{version}"
    bundle_dir = Path("workpackages/bundles") / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    try:
        (bundle_dir / "workpackage.json").write_text(
            json.dumps(
                {
                    "schema_version": "workpackage_schema.v1",
                    "mode": "blueprint_mode",
                    "workpackage": {
                        "id": workpackage_id,
                        "name": "地址治理",
                        "version": version,
                        "objective": "地址治理",
                        "scope": {"in_scope": ["normalization"], "out_of_scope": []},
                        "owner": {"team": "factory", "role": "dev"},
                        "priority": "P1",
                        "status": "aligned",
                        "acceptance_criteria": ["records 完整"],
                    },
                    "architecture_context": {
                        "factory_architecture": {"layers": ["agent", "runtime"]},
                        "runtime_env": {"python": "3.11"},
                    },
                    "io_contract": {"input_schema": {"type": "object"}, "output_schema": {"type": "object"}},
                    "api_plan": {
                        "registered_apis_used": [
                            {"source_id": "fengtu", "interface_id": "address_standardize"},
                            {"source_id": "fengtu", "interface_id": "address_real_check"},
                        ],
                        "missing_apis": [],
                    },
                    "execution_plan": {
                        "steps": [{"step_id": "S01", "name": "生成", "stage": "generate"}],
                        "gates": {
                            "confirm_generate": True,
                            "confirm_dryrun_result": True,
                            "confirm_publish": True,
                        },
                        "failure_handling": {
                            "on_schema_mismatch": "continue_llm_interaction_until_valid",
                            "on_api_failure": "block_error_no_fallback",
                            "on_dependency_missing": "ask_user_for_key_and_register",
                        },
                    },
                    "scripts": [
                        {
                            "name": "run_pipeline.py",
                            "purpose": "执行治理流程",
                            "runtime": "python3",
                            "entry": "python scripts/run_pipeline.py",
                            "dependencies": [],
                        }
                    ],
                    "skills": [
                        {
                            "skill_id": "nanobot_workpackage_schema_orchestrator",
                            "name": "nanobot 编排",
                            "path": "skills/nanobot_workpackage_schema_orchestrator.md",
                            "purpose": "补齐 schema",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        resp = client.get(
            "/v1/governance/observability/runtime/workpackage-blueprint"
            f"?workpackage_id={workpackage_id}&version={version}"
        )
        assert resp.status_code == 200
        payload = resp.json()
        selected_sources = payload.get("selected_sources") or []
        assert "fengtu" in selected_sources
    finally:
        shutil.rmtree(bundle_dir, ignore_errors=True)
