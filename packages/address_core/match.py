from __future__ import annotations

import re
from typing import List

from packages.address_core.normalize import normalize_text
from packages.address_core.parse import parse_components
from packages.address_core.trusted_fengtu import FengtuTrustedClient
from packages.address_core.types import MatchCandidate


def recall_candidates(normalized_text: str) -> List[MatchCandidate]:
    candidates: List[MatchCandidate] = []
    # Keep recall behavior consistent for both raw-text and normalized-text callers.
    text = normalize_text(str(normalized_text or ""))
    if not text:
        return candidates

    def _append(name: str, score: float, source: str) -> None:
        value = str(name or "")
        if not value:
            return
        if any(item.name == value for item in candidates):
            return
        candidates.append(MatchCandidate(name=value, score=score, source=source))

    _append(text, 0.75, "normalized_text")

    # "疑似不存在" 场景常带尾部地标词，截断到门牌形成核验候选。
    invalid_road = re.search(r"(不存在路\d+号)", text)
    if invalid_road:
        _append(text[: invalid_road.end(1)], 0.92, "invalid_road_truncate")

    # 根据解析字段重组前缀，补齐省市区与道路门牌结构。
    parsed = parse_components(text)
    parts = [
        parsed.get("province", ""),
        parsed.get("city", ""),
        parsed.get("district", ""),
        parsed.get("road", ""),
        parsed.get("house_no", ""),
    ]
    base = "".join([item for item in parts if item])
    if base:
        _append(base, 0.81, "parsed_prefix")
        tail_start = text.find(parsed.get("house_no", ""))
        tail = ""
        if tail_start >= 0 and parsed.get("house_no"):
            tail = text[tail_start + len(parsed["house_no"]) :]
        if tail:
            _append(f"{base}{tail}", 0.86, "parsed_recompose")
        else:
            _append(base, 0.83, "parsed_recompose")

    parsed_for_api = parsed
    fengtu = FengtuTrustedClient()
    standardized = fengtu.standardize(
        address=text,
        province=str(parsed_for_api.get("province", "")),
        city=str(parsed_for_api.get("city", "")),
        county=str(parsed_for_api.get("district", "")),
    )
    if standardized:
        _append(standardized, 0.94, "fengtu_standardize")

    real_check = fengtu.is_real_address(
        address=text,
        province=str(parsed_for_api.get("province", "")),
        city=str(parsed_for_api.get("city", "")),
        county=str(parsed_for_api.get("district", "")),
    )
    if real_check is False:
        _append(base or text, 0.35, "fengtu_real_check_invalid")

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates
