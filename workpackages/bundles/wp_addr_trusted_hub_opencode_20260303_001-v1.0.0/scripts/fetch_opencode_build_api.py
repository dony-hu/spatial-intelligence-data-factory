#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

generated_by = "opencode_agent"

def main() -> None:
    api_key = os.getenv("OPENCODE_API_KEY", "")
    payload = {
        "script": "fetch_opencode_build_api.py",
        "purpose": "调用外部API补齐能力：opencode_build_api",
        "endpoint": "https://api.opencode.ai/v1/build",
        "api_key_provided": bool(api_key),
        "status": "ready" if api_key else "waiting_for_api_key",
    }
    out = Path("output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "fetch_opencode_build_api.py.result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()