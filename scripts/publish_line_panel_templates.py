#!/usr/bin/env python3
"""Publish factory-owned panel templates for line repositories to consume."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "templates" / "line_debug_panel.template.html"
DST_DIR = PROJECT_ROOT / "output" / "factory_templates"


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"template not found: {SRC}")

    DST_DIR.mkdir(parents=True, exist_ok=True)
    dst = DST_DIR / SRC.name
    dst.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "template": dst.name,
        "published_at": datetime.now().isoformat(),
        "owner": "factory-project",
        "policy": "line repos must consume this template; avoid in-repo custom template html",
    }
    (DST_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"published: {dst}")


if __name__ == "__main__":
    main()
