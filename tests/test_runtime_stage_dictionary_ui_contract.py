from __future__ import annotations

from pathlib import Path

from services.governance_api.app.runtime_stage_dictionary import RUNTIME_PIPELINE_STAGE_ORDER


def test_runtime_stage_dictionary_is_declared_in_dashboard_ui() -> None:
    html = Path("web/dashboard/factory-agent-governance-prototype-v2.html").read_text(encoding="utf-8")
    for stage in RUNTIME_PIPELINE_STAGE_ORDER:
        assert stage in html
