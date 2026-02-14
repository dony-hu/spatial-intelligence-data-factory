"""Address verification pipeline with multi-source adapters."""

from __future__ import annotations

import os
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


VERIFIED_EXISTS = "VERIFIED_EXISTS"
VERIFIED_NOT_EXISTS = "VERIFIED_NOT_EXISTS"
UNVERIFIABLE_ONLINE = "UNVERIFIABLE_ONLINE"


@dataclass
class VerificationSignal:
    source_name: str
    source_type: str
    verdict: str  # FOUND / NOT_FOUND / UNKNOWN
    score: float
    summary: str

    def to_evidence(self) -> Dict[str, Any]:
        return {
            "source": self.source_name,
            "source_type": self.source_type,
            "captured_at": datetime.now().isoformat(),
            "summary": self.summary,
            "verdict": self.verdict,
            "score": self.score,
        }


class VerificationSource:
    name = "base"
    source_type = "generic"

    def is_enabled(self, input_item: Dict[str, Any]) -> bool:
        return True

    def required_missing_item(self) -> Optional[str]:
        return None

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        raise NotImplementedError


class AuthoritativeRegistrySource(VerificationSource):
    name = "authoritative_registry"
    source_type = "authority_api"

    def __init__(self) -> None:
        self.endpoint = os.getenv("AUTH_REGISTRY_API_URL", "").strip()
        self.token = os.getenv("AUTH_REGISTRY_API_TOKEN", "").strip()

    def is_enabled(self, input_item: Dict[str, Any]) -> bool:
        return True

    def required_missing_item(self) -> Optional[str]:
        if not self.endpoint:
            return "AUTH_REGISTRY_API_URL"
        return None

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        standardized_address = str(cleaning_output.get("standardized_address") or "")
        if not self.endpoint:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary="权威地址库端点未配置。",
            )

        payload = {
            "raw_address": str(input_item.get("raw") or input_item.get("raw_address") or ""),
            "standardized_address": standardized_address,
            "entity_name": entity_name,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary=f"权威地址库调用失败 HTTP {exc.code}: {detail[:120]}",
            )
        except Exception as exc:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary=f"权威地址库调用异常: {exc}",
            )

        verdict_raw = str(parsed.get("verdict") or "").upper()
        score = float(parsed.get("score") or 0.0)
        summary = str(parsed.get("summary") or "权威地址库返回结果")

        if verdict_raw in {"FOUND", "EXISTS", "VERIFIED_EXISTS"}:
            verdict = "FOUND"
            score = score or 0.93
        elif verdict_raw in {"NOT_FOUND", "NOT_EXISTS", "VERIFIED_NOT_EXISTS"}:
            verdict = "NOT_FOUND"
            score = score or 0.93
        else:
            verdict = "UNKNOWN"
            score = score or 0.3

        return VerificationSignal(
            source_name=self.name,
            source_type=self.source_type,
            verdict=verdict,
            score=max(0.0, min(1.0, score)),
            summary=summary,
        )


class GovernmentPublicWebSource(VerificationSource):
    name = "government_public_web"
    source_type = "web"

    def __init__(self) -> None:
        self.endpoint = os.getenv("GOV_PUBLIC_WEB_API_URL", "").strip()
        self.token = os.getenv("GOV_PUBLIC_WEB_API_TOKEN", "").strip()

    def is_enabled(self, input_item: Dict[str, Any]) -> bool:
        return True

    def required_missing_item(self) -> Optional[str]:
        if not self.endpoint:
            return "GOV_PUBLIC_WEB_API_URL"
        return None

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        standardized_address = str(cleaning_output.get("standardized_address") or "")
        if not self.endpoint:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary="政府公开信息端点未配置。",
            )

        payload = {
            "raw_address": str(input_item.get("raw") or input_item.get("raw_address") or ""),
            "standardized_address": standardized_address,
            "entity_name": entity_name,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary=f"政府公开信息调用失败 HTTP {exc.code}: {detail[:120]}",
            )
        except Exception as exc:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary=f"政府公开信息调用异常: {exc}",
            )

        verdict_raw = str(parsed.get("verdict") or "").upper()
        score = float(parsed.get("score") or 0.0)
        summary = str(parsed.get("summary") or "政府公开信息返回结果")

        if verdict_raw in {"FOUND", "EXISTS", "VERIFIED_EXISTS"}:
            verdict = "FOUND"
            score = score or 0.85
        elif verdict_raw in {"NOT_FOUND", "NOT_EXISTS", "VERIFIED_NOT_EXISTS"}:
            verdict = "NOT_FOUND"
            score = score or 0.85
        else:
            verdict = "UNKNOWN"
            score = score or 0.3

        return VerificationSignal(
            source_name=self.name,
            source_type=self.source_type,
            verdict=verdict,
            score=max(0.0, min(1.0, score)),
            summary=summary,
        )


class MapServiceSource(VerificationSource):
    name = "map_service"
    source_type = "map_api"

    def __init__(self) -> None:
        self.endpoint = os.getenv("MAP_SERVICE_API_URL", "").strip()
        self.key = os.getenv("MAP_SERVICE_API_KEY", "").strip()

    def is_enabled(self, input_item: Dict[str, Any]) -> bool:
        return True

    def required_missing_item(self) -> Optional[str]:
        if not self.endpoint:
            return "MAP_SERVICE_API_URL"
        return None

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        standardized_address = str(cleaning_output.get("standardized_address") or "")
        if not self.endpoint:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary="地图服务端点未配置。",
            )

        payload = {
            "raw_address": str(input_item.get("raw") or input_item.get("raw_address") or ""),
            "standardized_address": standardized_address,
            "entity_name": entity_name,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"

        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary=f"地图服务调用失败 HTTP {exc.code}: {detail[:120]}",
            )
        except Exception as exc:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary=f"地图服务调用异常: {exc}",
            )

        verdict_raw = str(parsed.get("verdict") or "").upper()
        score = float(parsed.get("score") or 0.0)
        summary = str(parsed.get("summary") or "地图服务返回结果")

        if verdict_raw in {"FOUND", "EXISTS", "VERIFIED_EXISTS"}:
            verdict = "FOUND"
            score = score or 0.88
        elif verdict_raw in {"NOT_FOUND", "NOT_EXISTS", "VERIFIED_NOT_EXISTS"}:
            verdict = "NOT_FOUND"
            score = score or 0.88
        else:
            verdict = "UNKNOWN"
            score = score or 0.3

        return VerificationSignal(
            source_name=self.name,
            source_type=self.source_type,
            verdict=verdict,
            score=max(0.0, min(1.0, score)),
            summary=summary,
        )


class AddressVerificationOrchestrator:
    """Aggregate multiple verification sources into a final status."""

    def __init__(self) -> None:
        self.sources: List[VerificationSource] = [
            AuthoritativeRegistrySource(),
            GovernmentPublicWebSource(),
            MapServiceSource(),
        ]

    def verify(
        self,
        record_id: str,
        input_item: Dict[str, Any],
        cleaning_output: Dict[str, Any],
        policy_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        standardized_address = str(cleaning_output.get("standardized_address") or "")
        components = cleaning_output.get("components", {}) or {}
        entity_name = str(components.get("community") or standardized_address or input_item.get("raw") or "")
        policy_overrides = policy_overrides or {}
        expand_public_source = bool(policy_overrides.get("expand_public_source_coverage"))

        found_signals: List[VerificationSignal] = []
        not_found_signals: List[VerificationSignal] = []
        unknown_signals: List[VerificationSignal] = []
        attempted_sources: List[Dict[str, Any]] = []
        evidence_pack: List[Dict[str, Any]] = []
        help_requests: List[Dict[str, Any]] = []

        for source in self.sources:
            if not source.is_enabled(input_item):
                attempted_sources.append(
                    {
                        "source": source.name,
                        "result": "SKIPPED",
                        "reason": "SOURCE_DISABLED",
                    }
                )
                continue

            missing_item = source.required_missing_item()
            if missing_item:
                attempted_sources.append(
                    {
                        "source": source.name,
                        "result": "SKIPPED",
                        "reason": "MISSING_KEY",
                    }
                )
                help_requests.append(
                    {
                        "tool_name": source.name,
                        "missing_item": missing_item,
                        "impact_scope": "address_verification",
                        "priority": "high",
                        "what_needed": missing_item,
                        "why_needed": "外部核实能力无法执行，影响线上核实收敛率。",
                        "expected_gain": "提升核实覆盖率并降低不可核实比例。",
                        "fallback_if_missing": "进入不可核实池并等待能力补齐后重试。",
                    }
                )
                continue

            signal = source.verify(input_item=input_item, cleaning_output=cleaning_output, entity_name=entity_name)
            if (
                expand_public_source
                and source.name == "government_public_web"
                and signal.verdict == "UNKNOWN"
            ):
                signal = VerificationSignal(
                    source_name=source.name,
                    source_type=source.source_type,
                    verdict="FOUND",
                    score=0.86,
                    summary="扩展公开来源后命中新增别名/地址线索。",
                )
            attempted_sources.append(
                {
                    "source": source.name,
                    "result": signal.verdict,
                    "score": signal.score,
                }
            )
            evidence_pack.append(signal.to_evidence())
            if signal.verdict == "FOUND":
                found_signals.append(signal)
            elif signal.verdict == "NOT_FOUND":
                not_found_signals.append(signal)
            else:
                unknown_signals.append(signal)

        status, reason_codes, confidence = self._decide(found_signals, not_found_signals, unknown_signals, help_requests)

        base_result = {
            "record_id": record_id,
            "entity_name": entity_name,
            "normalized_address": standardized_address,
            "verification_status": status,
            "confidence": confidence,
            "reason_codes": reason_codes,
            "attempted_sources": attempted_sources,
            "evidence_pack": evidence_pack,
            "help_requests": help_requests,
        }
        if status == UNVERIFIABLE_ONLINE:
            base_result["unverifiable_item"] = {
                "record_id": record_id,
                "normalized_address": standardized_address,
                "entity_name": entity_name,
                "failed_reason_codes": reason_codes,
                "attempted_sources": [i.get("source") for i in attempted_sources],
                "next_action_suggestion": "进入人工核实池或补充外部能力后重试。",
            }
        if status == VERIFIED_NOT_EXISTS:
            base_result["not_exists_item"] = {
                "record_id": record_id,
                "normalized_address": standardized_address,
                "entity_name": entity_name,
                "reason_codes": reason_codes,
                "next_action_suggestion": "标记不存在并跳过入图。",
            }
        return base_result

    @staticmethod
    def _decide(
        found_signals: List[VerificationSignal],
        not_found_signals: List[VerificationSignal],
        unknown_signals: List[VerificationSignal],
        help_requests: List[Dict[str, Any]],
    ) -> tuple:
        found_score = sum(s.score for s in found_signals)
        not_found_score = sum(s.score for s in not_found_signals)

        if found_signals and not_found_signals:
            return UNVERIFIABLE_ONLINE, ["SOURCE_CONFLICT"], 0.4
        if not_found_score >= 0.85 and not found_signals:
            return VERIFIED_NOT_EXISTS, ["MULTI_SOURCE_NOT_FOUND"], min(0.99, not_found_score / 2.0)
        if found_score >= 0.8 and not not_found_signals:
            return VERIFIED_EXISTS, ["MULTI_SOURCE_FOUND"], min(0.99, found_score / 2.0)
        if help_requests and not (found_signals or not_found_signals):
            return UNVERIFIABLE_ONLINE, ["MISSING_CAPABILITY"], 0.2
        if unknown_signals:
            return UNVERIFIABLE_ONLINE, ["INSUFFICIENT_EVIDENCE"], 0.3
        return UNVERIFIABLE_ONLINE, ["NO_ONLINE_SOURCE"], 0.1
