#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.address_core.parse import parse_components
from packages.address_core.trusted_fengtu import FengtuTrustedClient

DEFAULT_INPUT = ROOT / "testdata" / "fixtures" / "lab-mode-phase1_5-cn-address-cases-1000-2026-02-15.json"


def _load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"input must be a JSON array: {path}")
    rows: List[Dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _deep_find_string(payload: Any, keys: set[str]) -> str:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in keys and isinstance(value, str) and value.strip():
                return value.strip()
            hit = _deep_find_string(value, keys)
            if hit:
                return hit
    if isinstance(payload, list):
        for item in payload:
            hit = _deep_find_string(item, keys)
            if hit:
                return hit
    return ""


def _safe_get_fields(case_obj: Dict[str, Any]) -> Dict[str, str]:
    expected = case_obj.get("expected")
    if not isinstance(expected, dict):
        return {}
    normalized = expected.get("normalized")
    if not isinstance(normalized, dict):
        return {}
    fields = normalized.get("fields")
    if not isinstance(fields, dict):
        return {}
    return {str(k): str(v or "") for k, v in fields.items()}


def _hint_geo(case_obj: Dict[str, Any], raw: str) -> Tuple[str, str, str]:
    old_fields = _safe_get_fields(case_obj)
    province = str(old_fields.get("province", ""))
    city = str(old_fields.get("city", ""))
    county = str(old_fields.get("district", ""))

    if province and city and county:
        return province, city, county

    parsed_raw = parse_components(raw)
    province = province or str(parsed_raw.get("province", ""))
    city = city or str(parsed_raw.get("city", ""))
    county = county or str(parsed_raw.get("district", ""))
    return province, city, county


def _call_standardize(
    client: FengtuTrustedClient,
    *,
    raw: str,
    province: str,
    city: str,
    county: str,
) -> Tuple[str, str]:
    response = client.call(
        "address_standardize",
        {"address": raw, "province": province, "city": city, "county": county},
    )
    if not response.get("ok"):
        reason = str(response.get("reason", "call_failed"))
        return "", reason

    data = response.get("data")
    standardized = _deep_find_string(
        data,
        {
            "stdAddress",
            "standardizedAddress",
            "fullAddress",
            "full_address",
            "standard_address",
            "address",
            "result",
        },
    )
    if standardized:
        return standardized, ""

    # Common error-like messages returned with HTTP 200.
    detail = _deep_find_string(data, {"message", "msg", "error", "detail", "reason"})
    return "", (detail or "empty_standardize_response")


def _ensure_expected(case_obj: Dict[str, Any]) -> Dict[str, Any]:
    expected = case_obj.get("expected")
    if not isinstance(expected, dict):
        expected = {}
        case_obj["expected"] = expected

    normalized = expected.get("normalized")
    if not isinstance(normalized, dict):
        normalized = {}
        expected["normalized"] = normalized

    fields = normalized.get("fields")
    if not isinstance(fields, dict):
        fields = {
            "province": "",
            "city": "",
            "district": "",
            "street": "",
            "road": "",
            "no": "",
            "building": "",
            "unit": "",
            "room": "",
        }
        normalized["fields"] = fields

    # Keep key order stable by rebuilding dict.
    normalized["fields"] = {
        "province": str(fields.get("province", "")),
        "city": str(fields.get("city", "")),
        "district": str(fields.get("district", "")),
        "street": str(fields.get("street", "")),
        "road": str(fields.get("road", "")),
        "no": str(fields.get("no", "")),
        "building": str(fields.get("building", "")),
        "unit": str(fields.get("unit", "")),
        "room": str(fields.get("room", "")),
    }

    return expected


def _apply_standardized(case_obj: Dict[str, Any], standardized: str) -> None:
    expected = _ensure_expected(case_obj)
    normalized = expected["normalized"]
    old_fields = _safe_get_fields(case_obj)

    parsed = parse_components(standardized)
    fields = {
        "province": str(parsed.get("province", "")),
        "city": str(parsed.get("city", "")),
        "district": str(parsed.get("district", "")),
        "street": str(old_fields.get("street", "")),
        "road": str(parsed.get("road", "")),
        "no": str(parsed.get("house_no", "")),
        "building": str(parsed.get("building", "")),
        "unit": str(parsed.get("unit", "")),
        "room": str(parsed.get("room", "")),
    }

    normalized["canon_text"] = standardized
    normalized["fields"] = fields

    evidence = expected.get("evidence_expected")
    if not isinstance(evidence, list):
        evidence = []
    if "丰图地址标准化接口命中" not in evidence:
        evidence = ["丰图地址标准化接口命中", *[str(x) for x in evidence]]
    expected["evidence_expected"] = evidence


def _write(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Use Fengtu address_standardize to build expected normalized outputs")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input JSON array file")
    parser.add_argument("--output", default="", help="Output JSON file; defaults to <input>.fengtu.json")
    parser.add_argument("--in-place", action="store_true", help="Overwrite input file")
    parser.add_argument("--limit", type=int, default=0, help="Only process first N cases (0 means all)")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Sleep milliseconds between API calls")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any case fails to standardize")
    parser.add_argument("--enable-fengtu", action="store_true", help="Set ADDRESS_TRUSTED_FENGTU_ENABLED=1")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"input not found: {input_path}")

    if args.enable_fengtu:
        os.environ["ADDRESS_TRUSTED_FENGTU_ENABLED"] = "1"

    rows = _load_cases(input_path)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    client = FengtuTrustedClient()

    total = len(rows)
    updated = 0
    failed = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []
    fail_reason_counter: Dict[str, int] = {}

    for idx, case_obj in enumerate(rows, start=1):
        raw = str(case_obj.get("input_raw", "")).strip()
        if not raw:
            skipped += 1
            continue

        province, city, county = _hint_geo(case_obj, raw)
        standardized, fail_reason = _call_standardize(
            client,
            raw=raw,
            province=province,
            city=city,
            county=county,
        )

        if standardized and str(standardized).strip():
            _apply_standardized(case_obj, str(standardized).strip())
            updated += 1
        else:
            failed += 1
            reason = str(fail_reason or "standardize_empty")
            fail_reason_counter[reason] = int(fail_reason_counter.get(reason, 0)) + 1
            state = FengtuTrustedClient.network_confirmation_state()
            errors.append(
                {
                    "index": idx,
                    "description": str(case_obj.get("description", "")),
                    "input_raw": raw,
                    "province": province,
                    "city": city,
                    "county": county,
                    "reason": reason,
                    "network_state": state,
                }
            )

        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    if args.in_place:
        output_path = input_path
        output_rows = rows
    else:
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_suffix("").with_name(input_path.stem + ".fengtu").with_suffix(".json")

        all_rows = _load_cases(input_path)
        if args.limit and args.limit > 0:
            all_rows[: len(rows)] = rows
            output_rows = all_rows
        else:
            output_rows = rows

    _write(output_path, output_rows)

    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "total_processed": total,
        "updated": updated,
        "failed": failed,
        "skipped": skipped,
        "enabled": client.enabled(),
        "fail_reason_counter": fail_reason_counter,
        "errors_preview": errors[:10],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.strict and failed > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
