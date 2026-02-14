from __future__ import annotations

import os
import sys


def ensure_demo_allowed(script_name: str) -> None:
    if os.getenv("ALLOW_DEMO_SCRIPTS", "0") == "1":
        return
    print(
        f"[blocked] {script_name} 已被禁用（默认屏蔽 mock/demo 流程）。\n"
        "如需强制运行请先设置 ALLOW_DEMO_SCRIPTS=1。\n"
        "建议改用: PYTHONPATH=\"$PWD\" /Users/huda/Code/.venv/bin/python scripts/run_governance_e2e_minimal.py"
    )
    raise SystemExit(2)
