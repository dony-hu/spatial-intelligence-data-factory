#!/usr/bin/env python3
from __future__ import annotations

import json

from dashboard_data_lib import EVENTS_PATH, build_all, write_outputs


def main() -> int:
    payloads = build_all()
    write_outputs(payloads)
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVENTS_PATH.touch(exist_ok=True)
    print(json.dumps({"ok": True, "written": sorted(payloads.keys())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
