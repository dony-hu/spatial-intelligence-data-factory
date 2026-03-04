#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

generated_by = "opencode_agent"

def main() -> None:
    api_key = os.getenv("EXTERNAL_API_KEY", "")
    payload = {
        "script": "external_route_matrix_client.py",
        "purpose": "调用高德/百度路线矩阵接口，生成graph边distance_m与travel_time_s",
        "endpoint": "",
        "api_key_provided": bool(api_key),
        "status": "ready" if api_key else "waiting_for_api_key",
    }
    out = Path("output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "external_route_matrix_client.py.result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()