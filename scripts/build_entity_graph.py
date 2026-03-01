#!/usr/bin/env python3
"""PG-only guard for deprecated entity graph builder."""

from __future__ import annotations

import sys


def main() -> int:
    print("[blocked] scripts/build_entity_graph.py 已下线：旧版本地数据库实现已移除（PG-only）。")
    print("请改用地址治理主链路与 PG Runtime 产物进行图谱构建。")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
