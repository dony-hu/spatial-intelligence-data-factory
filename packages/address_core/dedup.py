from __future__ import annotations

from typing import Dict, Set


def dedup_records(records: list[Dict[str, str]]) -> list[Dict[str, str]]:
    seen: Set[str] = set()
    unique_records: list[Dict[str, str]] = []
    for item in records:
        key = f"{item.get('raw_id','')}::{item.get('raw_text','')}"
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(item)
    return unique_records
