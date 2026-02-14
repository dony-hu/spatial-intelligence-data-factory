from __future__ import annotations

from typing import Dict, List, Tuple

from packages.address_core.types import MatchCandidate


def score_confidence(parsed: Dict[str, str], candidates: List[MatchCandidate]) -> Tuple[float, str]:
    field_score = min(len(parsed) / 5.0, 1.0)
    candidate_score = candidates[0].score if candidates else 0.0
    confidence = round((field_score * 0.6 + candidate_score * 0.4), 4)

    if confidence >= 0.85:
        strategy = "rule_only"
    elif confidence >= 0.6:
        strategy = "match_dict"
    else:
        strategy = "human_required"
    return confidence, strategy
