#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from scripts._mode_guard import ensure_demo_allowed

ADDR = "深圳市南山区前海顺丰总部大厦"
AK_TEST = "a0ece06a144a42228cd074e527a4f14f"
AK_TEST2 = "0748238c55024ea88a61815232a53714"


def call(name: str, url: str, method: str = "GET", headers: dict | None = None, query: dict | None = None):
    headers = headers or {}
    query = query or {}
    full_url = f"{url}?{urllib.parse.urlencode(query)}" if query else url
    req = urllib.request.Request(full_url, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(text)
            except Exception:
                body = text
            print(json.dumps({"name": name, "http": resp.getcode(), "body": body}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"name": name, "error": str(exc)}, ensure_ascii=False))


def main() -> int:
    ensure_demo_allowed("scripts/probe_209_173.py")
    call(
        "209/header/full",
        "https://gis-apis.sf-express.com/iad/api",
        headers={"ak": AK_TEST2},
        query={"address": ADDR, "province": "广东省", "city": "深圳市", "county": "南山区", "town": "南山街道"},
    )
    call(
        "209/query-ak/min",
        "https://gis-apis.sf-express.com/iad/api",
        query={"ak": AK_TEST2, "address": ADDR},
    )

    call(
        "173/header/755/aoi",
        "https://gis-apis.sf-express.com/atype/api",
        headers={"ak": AK_TEST},
        query={"address": ADDR, "citycode": "755", "opt": "aoi"},
    )
    call(
        "173/header/7551/aoi",
        "https://gis-apis.sf-express.com/atype/api",
        headers={"ak": AK_TEST},
        query={"address": ADDR, "citycode": "7551", "opt": "aoi"},
    )
    call(
        "173/query-ak/755/aoi",
        "https://gis-apis.sf-express.com/atype/api",
        query={"ak": AK_TEST, "address": ADDR, "citycode": "755", "opt": "aoi"},
    )
    call(
        "173/query-ak/755/defaultopt",
        "https://gis-apis.sf-express.com/atype/api",
        query={"ak": AK_TEST, "address": ADDR, "citycode": "755"},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
