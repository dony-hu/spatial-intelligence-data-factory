#!/usr/bin/env python3
"""地址治理 MVP 验收（真实 LLM 门禁剖面）。"""

from __future__ import annotations

import sys

from run_address_governance_mvp_acceptance import main_with_args


def main() -> int:
    return main_with_args(["--profile", "real-llm-gate", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
