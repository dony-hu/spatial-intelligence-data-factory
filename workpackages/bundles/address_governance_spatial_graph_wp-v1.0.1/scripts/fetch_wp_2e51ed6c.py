#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

generated_by = "opencode_agent"

def main() -> None:
    api_key = os.getenv("AMAP_WEB_API_KEY", "")
    payload = {
        "script": "fetch_wp_2e51ed6c.py",
        "purpose": "调用外部API补齐能力：路径距离矩阵（驾车/步行）",
        "endpoint": "https://restapi.amap.com/v3/distance",
        "api_key_provided": bool(api_key),
        "status": "ready" if api_key else "waiting_for_api_key",
    }
    out = Path("output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "fetch_wp_2e51ed6c.py.result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()