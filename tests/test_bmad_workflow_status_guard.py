from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml


def test_bmad_workflow_last_updated_not_in_future() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    status_path = repo_root / "docs" / "bmm-workflow-status.yaml"
    payload = yaml.safe_load(status_path.read_text(encoding="utf-8")) or {}
    last_updated = str(payload.get("last_updated") or "").strip()
    assert last_updated, "docs/bmm-workflow-status.yaml missing last_updated"
    assert date.fromisoformat(last_updated) <= date.today()
