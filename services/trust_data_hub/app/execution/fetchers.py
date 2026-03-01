from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any


def _resolve_file_path(path: Path) -> Path:
    if path.exists():
        return path
    marker = "spatial-intelligence-data-factory/"
    raw = str(path)
    if marker in raw:
        suffix = raw.split(marker, 1)[1]
        project_root = Path(__file__).resolve().parents[4]
        candidate = project_root / suffix
        if candidate.exists():
            return candidate
    return path


def fetch_payload(source: dict[str, Any]) -> dict[str, Any]:
    entrypoint = str(source.get("entrypoint") or "").strip()
    if entrypoint.startswith("file://"):
        path = _resolve_file_path(Path(entrypoint.replace("file://", "", 1)))
        return json.loads(path.read_text(encoding="utf-8"))

    if entrypoint.startswith("http://") or entrypoint.startswith("https://"):
        with urllib.request.urlopen(entrypoint, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)

    return {}
