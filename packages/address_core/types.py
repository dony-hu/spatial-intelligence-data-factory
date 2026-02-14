from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RawAddressRecord:
    raw_id: str
    raw_text: str
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    street: Optional[str] = None
    detail: Optional[str] = None


@dataclass
class MatchCandidate:
    name: str
    score: float
    source: str


@dataclass
class GovernanceResult:
    raw_id: str
    canon_text: str
    confidence: float
    strategy: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    candidates: List[MatchCandidate] = field(default_factory=list)
