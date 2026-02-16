from __future__ import annotations

from typing import Dict, Set

from packages.address_core.normalize import normalize_text


def dedup_records(records: list[Dict[str, str]]) -> list[Dict[str, str]]:
    seen: Set[str] = set()
    unique_records: list[Dict[str, str]] = []
    for item in records:
        raw_text = str(item.get("raw_text", "") or "")
        normalized = normalize_text(raw_text) if raw_text else ""
        key = normalized or raw_text.strip() or str(item.get("raw_id", "") or "")
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(item)
    return unique_records
