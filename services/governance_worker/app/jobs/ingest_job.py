from __future__ import annotations

from hashlib import sha256


def run(task_payload: dict) -> dict:
    records = task_payload.get("records", [])
    for item in records:
        item.setdefault("raw_hash", sha256(item.get("raw_text", "").encode("utf-8")).hexdigest())
    task_payload["records"] = records
    return task_payload
