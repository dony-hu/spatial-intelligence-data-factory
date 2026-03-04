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
