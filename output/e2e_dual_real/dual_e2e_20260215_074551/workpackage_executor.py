#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
from urllib import parse, request


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_interface(trusted_cfg: Dict[str, Any], interface_id: str) -> Dict[str, Any]:
    for src in list(trusted_cfg.get("trusted_sources") or []):
        for it in list(src.get("trusted_interfaces") or []):
            if str(it.get("interface_id")) == str(interface_id):
                return dict(it)
    raise RuntimeError(f"interface not found: {interface_id}")


def _fill_template(value: Any, record: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        out = value
        for k, v in record.items():
            out = out.replace(" + str(k) + ", str(v))
        return out
    if isinstance(value, dict):
        return {k: _fill_template(v, record) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill_template(v, record) for v in value]
    return value


def _call_interface(it: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    method = str(it.get("method") or "GET").upper()
    base_url = str(it.get("base_url") or "").strip()
    headers = dict(it.get("headers") or {})
    template = dict(it.get("request_template") or {})
    query = _fill_template(template.get("query") or {}, record)
    body = _fill_template(template.get("body") or {}, record)

    if str(it.get("ak_in") or "").lower() == "query" and "ak" not in query and "ak" in headers:
        query["ak"] = headers["ak"]
        headers = {k: v for k, v in headers.items() if k.lower() != "ak"}

    url = base_url
    if query:
        url = f"{base_url}?{parse.urlencode(query)}"

    data = None
    if method in {"POST", "PUT", "PATCH"}:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")

    req = request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(raw)
            return {"ok": True, "http_status": int(resp.status), "body": payload}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute generated address governance workpackage")
    parser.add_argument("--workpackage", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    wp = _load_json(Path(args.workpackage))
    cases = _load_json(Path(args.cases))
    trusted_cfg = _load_json(Path("/Users/huda/Code/worktrees/factory-address-verify/config/trusted_data_sources.json"))

    sequence = list(wp.get("interface_sequence") or [])
    records = list(cases.get("records") or [])
    outputs: List[Dict[str, Any]] = []

    for rec in records:
        evidence_items: List[Dict[str, Any]] = []
        ok_count = 0
        for interface_id in sequence:
            it = _find_interface(trusted_cfg, str(interface_id))
            res = _call_interface(it, rec)
            if res.get("ok"):
                ok_count += 1
            evidence_items.append({
                "interface_id": interface_id,
                "ok": bool(res.get("ok")),
                "result": res,
            })

        confidence = (ok_count / len(sequence)) if sequence else 0.0
        outputs.append({
            "raw_id": rec.get("raw_id"),
            "canon_text": str(rec.get("raw_text") or "").strip(),
            "confidence": round(float(confidence), 4),
            "strategy": "trusted_interface_chain",
            "evidence": {"items": evidence_items},
        })

    out = {"results": outputs, "sequence": sequence}
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
