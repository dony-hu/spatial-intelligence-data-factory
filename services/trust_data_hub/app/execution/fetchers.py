from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any


def fetch_payload(source: dict[str, Any]) -> dict[str, Any]:
    entrypoint = str(source.get("entrypoint") or "").strip()
    if entrypoint.startswith("file://"):
        path = Path(entrypoint.replace("file://", "", 1))
        return json.loads(path.read_text(encoding="utf-8"))

    if entrypoint.startswith("http://") or entrypoint.startswith("https://"):
        with urllib.request.urlopen(entrypoint, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)

    return {}
