from __future__ import annotations

from typing import Any


def _default_payload(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "admin_division": list(raw.get("admin_division") or []),
        "roads": list(raw.get("roads") or []),
        "pois": list(raw.get("pois") or []),
        "places": list(raw.get("places") or []),
    }


def _parse_osm_elements_v1(raw: dict[str, Any]) -> dict[str, Any]:
    roads: list[dict[str, Any]] = []
    pois: list[dict[str, Any]] = []

    for element in list(raw.get("elements") or []):
        tags = element.get("tags") or {}
        name = str(tags.get("name") or "").strip()
        adcode = str(tags.get("addr:adcode") or "")
        if element.get("type") == "way" and name:
            roads.append(
                {
                    "road_id": f"osm-way-{element.get('id')}",
                    "name": name,
                    "normalized_name": name,
                    "admin_adcode": adcode,
                }
            )
        if element.get("type") == "node" and name:
            lat = element.get("lat")
            lon = element.get("lon")
            centroid = None
            if lat is not None and lon is not None:
                centroid = f"{lon},{lat}"
            pois.append(
                {
                    "poi_id": f"osm-node-{element.get('id')}",
                    "name": name,
                    "normalized_name": name,
                    "category": str(tags.get("amenity") or "unknown"),
                    "admin_adcode": adcode,
                    "centroid": centroid,
                }
            )

    return {
        "admin_division": [],
        "roads": roads,
        "pois": pois,
        "places": [],
    }


def parse_raw_payload(raw: dict[str, Any], parser_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = parser_profile or {}
    variant = str(profile.get("dataset_variant") or "").strip()
    if variant in {"file_json", "admin_v1", "admin_v2", ""}:
        return _default_payload(raw)
    if variant == "osm_elements_v1":
        return _parse_osm_elements_v1(raw)
    return _default_payload(raw)
