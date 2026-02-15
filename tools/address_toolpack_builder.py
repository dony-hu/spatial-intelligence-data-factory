"""Factory-side toolpack builder: generate address toolpack from map API (+ optional LLM iteration)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.agent_cli import load_config, run_requirement_query


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    raw = str(text or "").strip()
    if not raw:
        return None
    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw, flags=re.IGNORECASE)
    if fence:
        candidates.append(fence.group(1))
    brace = re.search(r"(\{[\s\S]*\})", raw)
    if brace:
        candidates.append(brace.group(1))
    for item in candidates:
        try:
            obj = json.loads(item)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


class AddressToolpackBuilder:
    def __init__(
        self,
        map_api_url: str,
        map_api_key: str = "",
        llm_config_path: str = "config/llm_api.json",
        enable_llm_iteration: bool = True,
    ) -> None:
        self.map_api_url = map_api_url.strip()
        self.map_api_key = map_api_key.strip()
        self.llm_config_path = llm_config_path
        self.enable_llm_iteration = enable_llm_iteration

    def build(self, seed_addresses: List[str]) -> Dict[str, Any]:
        if not self.map_api_url:
            raise RuntimeError("MAP_TOOLPACK_API_URL is required")

        observations: List[Dict[str, str]] = []
        failures: List[Dict[str, str]] = []
        for raw in seed_addresses:
            query = str(raw or "").strip()
            if not query:
                continue
            try:
                obs = self._lookup_map(query)
                if obs.get("city") and obs.get("district"):
                    observations.append(obs)
                else:
                    failures.append({"query": query, "reason": "empty city/district"})
            except Exception as exc:
                failures.append({"query": query, "reason": str(exc)})

        base = self._build_deterministic_toolpack(observations)
        warnings: List[str] = []

        if self.enable_llm_iteration and observations:
            try:
                cfg = load_config(self.llm_config_path)
                llm_toolpack = self._llm_refine(observations, cfg)
                if llm_toolpack:
                    base["cities"] = llm_toolpack.get("cities", base.get("cities", []))
                    base["llm_refined"] = True
                else:
                    warnings.append("llm_refine_empty")
            except Exception as exc:
                warnings.append(f"llm_refine_failed: {exc}")

        base["seed_count"] = len(seed_addresses)
        base["observation_count"] = len(observations)
        base["failed_queries"] = failures
        base["warnings"] = warnings
        return base

    def _lookup_map(self, query: str) -> Dict[str, str]:
        payload = json.dumps({"query": query}, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.map_api_key:
            headers["Authorization"] = f"Bearer {self.map_api_key}"
        req = urllib.request.Request(self.map_api_url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
            raise RuntimeError(f"map_api_http_{exc.code}: {detail[:160]}") from exc
        except Exception as exc:
            raise RuntimeError(f"map_api_request_failed: {exc}") from exc

        # tolerant extraction
        if isinstance(parsed.get("top"), dict):
            top = parsed["top"]
        elif isinstance(parsed.get("candidates"), list) and parsed["candidates"]:
            top = parsed["candidates"][0]
        else:
            top = parsed

        city = str(top.get("city") or "").strip()
        district = str(top.get("district") or "").strip()
        city_alias = str(top.get("city_alias") or city).strip()
        district_alias = str(top.get("district_alias") or district).strip()
        return {
            "city": city,
            "district": district,
            "city_alias": city_alias,
            "district_alias": district_alias,
        }

    @staticmethod
    def _build_deterministic_toolpack(observations: List[Dict[str, str]]) -> Dict[str, Any]:
        by_city: Dict[str, Dict[str, Any]] = {}
        for item in observations:
            city = str(item.get("city") or "").strip()
            district = str(item.get("district") or "").strip()
            city_alias = str(item.get("city_alias") or city).strip()
            district_alias = str(item.get("district_alias") or district).strip()
            if not city or not district:
                continue
            city_entry = by_city.setdefault(city, {"name": city, "aliases": set(), "districts": {}})
            if city_alias:
                city_entry["aliases"].add(city_alias)
            district_entry = city_entry["districts"].setdefault(district, {"name": district, "aliases": set()})
            if district_alias:
                district_entry["aliases"].add(district_alias)

        cities: List[Dict[str, Any]] = []
        for city_name in sorted(by_city.keys()):
            city_entry = by_city[city_name]
            districts: List[Dict[str, Any]] = []
            for district_name in sorted(city_entry["districts"].keys()):
                district_entry = city_entry["districts"][district_name]
                aliases = sorted({a for a in district_entry["aliases"] if a and a != district_name})
                districts.append({"name": district_name, "aliases": aliases})
            city_aliases = sorted({a for a in city_entry["aliases"] if a and a != city_name})
            cities.append({"name": city_name, "aliases": city_aliases, "districts": districts})

        return {
            "version": f"{datetime.now().strftime('%Y-%m-%d')}.factory.generated.1",
            "description": "Generated by factory from map API observations",
            "generation_mode": "factory_generated",
            "llm_refined": False,
            "generated_at": datetime.now().isoformat(),
            "cities": cities,
        }

    def _llm_refine(self, observations: List[Dict[str, str]], config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        prompt = (
            "你是地址工具包归并器。请把观测样本归并为严格JSON对象，结构为: "
            "{\"cities\":[{\"name\":\"\",\"aliases\":[],\"districts\":[{\"name\":\"\",\"aliases\":[]}]}]}。"
            "禁止输出解释文字。"
            f"样本: {json.dumps(observations, ensure_ascii=False)}"
        )
        result = run_requirement_query(requirement=prompt, config=config)
        answer = str(result.get("answer") or "")
        parsed = _extract_json_object(answer)
        if not parsed:
            return None
        cities = parsed.get("cities")
        if not isinstance(cities, list):
            return None
        return {"cities": cities}
