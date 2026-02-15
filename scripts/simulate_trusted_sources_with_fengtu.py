#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict
from scripts._mode_guard import ensure_demo_allowed

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "trusted_data_sources.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_PATH = OUTPUT_DIR / "trusted_sources_simulation_fengtu.json"


def _fill_template(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        out = value
        for key, val in context.items():
            out = out.replace(f"{{{key}}}", str(val))
        return out
    if isinstance(value, dict):
        return {k: _fill_template(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill_template(v, context) for v in value]
    return value


def main() -> int:
    ensure_demo_allowed("scripts/simulate_trusted_sources_with_fengtu.py")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    trusted_sources = list(cfg.get("trusted_sources") or [])

    template_context = {
        "address": "深圳市南山区前海顺丰总部大厦",
        "province": "广东省",
        "city": "深圳市",
        "county": "南山区",
        "town": "南山街道",
        "citycode": "755",
        "company": "顺丰",
    }

    results = []
    for src in trusted_sources:
        source_id = src.get("source_id")
        source_name = src.get("name")
        interfaces = src.get("trusted_interfaces") or []

        if interfaces:
            targets = []
            for itf in interfaces:
                req_tpl = itf.get("request_template") or {}
                targets.append(
                    {
                        "interface_id": itf.get("interface_id"),
                        "interface_name": itf.get("name"),
                        "doc_url": itf.get("doc_url"),
                        "base_url": itf.get("base_url"),
                        "method": str(itf.get("method") or "GET").upper(),
                        "headers": dict(itf.get("headers") or {}),
                        "query": _fill_template(req_tpl.get("query") or {}, template_context),
                        "body": _fill_template(req_tpl.get("body") or {}, template_context),
                    }
                )
        else:
            req_cfg = src.get("request") or {}
            targets = [
                {
                    "interface_id": "default",
                    "interface_name": "default",
                    "doc_url": None,
                    "base_url": src.get("base_url"),
                    "method": str(req_cfg.get("method") or "GET").upper(),
                    "headers": dict(req_cfg.get("headers") or {}),
                    "query": _fill_template(req_cfg.get("query_template") or {}, template_context),
                    "body": {},
                }
            ]

        for target in targets:
            base_url = target.get("base_url")
            method = str(target.get("method") or "GET").upper()
            headers = dict(target.get("headers") or {})
            query = dict(target.get("query") or {})
            body = dict(target.get("body") or {})

            full_url = f"{base_url}?{urllib.parse.urlencode(query)}" if query else str(base_url)
            data = None
            if method in {"POST", "PUT", "PATCH"}:
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                headers.setdefault("Content-Type", "application/json")

            req = urllib.request.Request(full_url, data=data, method=method, headers=headers)

            item = {
                "source_id": source_id,
                "source_name": source_name,
                "interface_id": target.get("interface_id"),
                "interface_name": target.get("interface_name"),
                "doc_url": target.get("doc_url"),
                "request": {
                    "method": method,
                    "base_url": base_url,
                    "query": query,
                    "body": body if body else None,
                    "headers": {**headers, "ak": "***MASKED***"} if "ak" in headers else headers,
                },
            }

            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    body_text = resp.read().decode("utf-8", errors="replace")
                    item["response"] = {
                        "http_status": resp.getcode(),
                    }
                    try:
                        payload = json.loads(body_text)
                        item["response"]["body"] = payload
                        item["pass"] = bool(resp.getcode() == 200 and payload.get("status") == 0)
                    except Exception:
                        item["response"]["body"] = body_text
                        item["pass"] = False
            except Exception as exc:
                item["error"] = str(exc)
                item["pass"] = False

            results.append(item)

    summary = {
        "config_path": str(CONFIG_PATH),
        "total": len(results),
        "pass_count": sum(1 for x in results if x.get("pass")),
        "results": results,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
