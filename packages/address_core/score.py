from __future__ import annotations

from typing import Dict, List, Tuple

from packages.address_core.types import MatchCandidate


def score_confidence(parsed: Dict[str, str], candidates: List[MatchCandidate]) -> Tuple[float, str]:
    field_score = min(len(parsed) / 5.0, 1.0)
    candidate_score = candidates[0].score if candidates else 0.0
    confidence = field_score * 0.65 + candidate_score * 0.35

    # Hard risk signals should pull score to reject/review.
    if not parsed.get("house_no"):
        confidence -= 0.4
    if not parsed.get("district"):
        confidence -= 0.2
    if not parsed.get("road"):
        confidence -= 0.2

    # Structure likely incomplete: has building+room but missing unit.
    if parsed.get("building") and parsed.get("room") and not parsed.get("unit"):
        confidence -= 0.17

    top_name = candidates[0].name if candidates else ""
    if "不存在路" in top_name:
        confidence -= 0.45
    if any(item.source == "invalid_road_truncate" for item in candidates):
        confidence -= 0.2
    if any(item.source == "fengtu_real_check_invalid" for item in candidates):
        confidence -= 0.35

    confidence = round(max(0.0, min(1.0, confidence)), 4)

    if confidence >= 0.88:
        strategy = "rule_only"
    elif confidence >= 0.62:
        strategy = "match_dict"
    else:
        strategy = "human_required"
    return confidence, strategy
