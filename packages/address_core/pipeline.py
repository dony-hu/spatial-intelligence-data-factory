from __future__ import annotations

from typing import Any, Dict, List

from packages.address_core.dedup import dedup_records
from packages.address_core.match import recall_candidates
from packages.address_core.normalize import normalize_text
from packages.address_core.parse import parse_components
from packages.address_core.score import score_confidence


def _query_trust_enhancement(
    *,
    trust_provider: Any,
    ruleset: Dict[str, Any],
    parsed: Dict[str, str],
) -> list[dict[str, Any]]:
    namespace = str(ruleset.get("trust_namespace") or "")
    evidence_items: list[dict[str, Any]] = []

    admin_name = str(parsed.get("district") or parsed.get("city") or parsed.get("province") or "").strip()
    if admin_name and hasattr(trust_provider, "query_admin_division"):
        rows = trust_provider.query_admin_division(namespace=namespace, name=admin_name, parent_hint=None) or []
        evidence_items.append(
            {
                "step": "trust_query",
                "domain": "admin_division",
                "namespace": namespace,
                "query": admin_name,
                "count": len(rows),
            }
        )

    road_name = str(parsed.get("road") or "").strip()
    if road_name and hasattr(trust_provider, "query_road"):
        rows = trust_provider.query_road(namespace=namespace, name=road_name, adcode_hint=None) or []
        evidence_items.append(
            {
                "step": "trust_query",
                "domain": "road",
                "namespace": namespace,
                "query": road_name,
                "count": len(rows),
            }
        )

    poi_name = road_name or admin_name
    if poi_name and hasattr(trust_provider, "query_poi"):
        rows = trust_provider.query_poi(namespace=namespace, name=poi_name, adcode_hint=None, top_k=5) or []
        evidence_items.append(
            {
                "step": "trust_query",
                "domain": "poi",
                "namespace": namespace,
                "query": poi_name,
                "count": len(rows),
            }
        )

    return evidence_items


def run(records: List[Dict[str, Any]], ruleset: Dict[str, Any], trust_provider: Any | None = None) -> List[Dict[str, Any]]:
    if not records:
        raise ValueError("blocked: input records are empty")
    unique_records = dedup_records(records)
    if not unique_records:
        raise ValueError("blocked: no valid unique records")
    trust_required = bool(ruleset.get("require_trust_enhancement", False))
    if trust_required and trust_provider is None:
        raise ValueError("blocked: trust provider is required by ruleset")

    outputs: List[Dict[str, Any]] = []
    for item in unique_records:
        raw_text = str(item.get("raw_text", "")).strip()
        if not raw_text:
            raise ValueError(f"blocked: raw_text empty for raw_id={item.get('raw_id')}")
        normalized = normalize_text(raw_text)
        parsed = parse_components(normalized)
        candidates = recall_candidates(normalized)
        confidence, strategy = score_confidence(parsed, candidates)
        trust_evidence_items: list[dict[str, Any]] = []
        if trust_provider is not None:
            try:
                trust_evidence_items = _query_trust_enhancement(trust_provider=trust_provider, ruleset=ruleset, parsed=parsed)
            except Exception as exc:
                if trust_required:
                    raise ValueError(f"blocked: trust enhancement failed: {exc.__class__.__name__}") from exc
                trust_evidence_items.append(
                    {
                        "step": "trust_query",
                        "status": "error",
                        "error_type": exc.__class__.__name__,
                    }
                )

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
                        *trust_evidence_items,
                    ]
                },
            }
        )
    return outputs
