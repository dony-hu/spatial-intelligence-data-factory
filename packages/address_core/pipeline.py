from __future__ import annotations

from typing import Any, Dict, List

from packages.address_core.dedup import dedup_records
from packages.address_core.match import recall_candidates
from packages.address_core.normalize import normalize_text
from packages.address_core.parse import parse_components
from packages.address_core.score import score_confidence


def run(records: List[Dict[str, Any]], ruleset: Dict[str, Any]) -> List[Dict[str, Any]]:
    unique_records = dedup_records(records)
    outputs: List[Dict[str, Any]] = []
    for item in unique_records:
        normalized = normalize_text(str(item.get("raw_text", "")))
        parsed = parse_components(normalized)
        candidates = recall_candidates(normalized)
        confidence, strategy = score_confidence(parsed, candidates)

        outputs.append(
            {
                "raw_id": item.get("raw_id"),
                "canon_text": normalized,
                "confidence": confidence,
                "strategy": strategy,
                "evidence": {
                    "items": [
                        {"step": "normalize", "value": normalized},
                        {"step": "parse", "fields": list(parsed.keys())},
                        {"step": "candidate_count", "count": len(candidates)},
                        {"step": "ruleset", "value": ruleset.get("ruleset_id", "default")},
                    ]
                },
            }
        )
    return outputs
