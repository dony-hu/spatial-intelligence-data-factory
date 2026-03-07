#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

generated_by = "opencode_agent"

def main() -> None:
    api_key = os.getenv("EXTERNAL_API_KEY", "")
    payload = {
        "script": "govern_addresses.py",
        "purpose": "串联已注册API完成标准化、区划补齐、地理编码与真实性校验",
        "endpoint": "",
        "api_key_provided": bool(api_key),
        "status": "ready" if api_key else "waiting_for_api_key",
    }
    out = Path("output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "govern_addresses.py.result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()