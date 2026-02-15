from __future__ import annotations

from typing import List

from packages.address_core.types import MatchCandidate


def recall_candidates(normalized_text: str) -> List[MatchCandidate]:
    candidates: List[MatchCandidate] = []
    if normalized_text:
        candidates.append(MatchCandidate(name=normalized_text, score=0.75, source="normalized_text"))
    return candidates
