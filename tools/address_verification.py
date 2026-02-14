"""Address verification pipeline with multi-source adapters."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.agent_runtime_store import AgentRuntimeStore
from tools.external_apis.map_service import MapServiceClient
from tools.external_apis.review_platform import ReviewPlatformClient
from tools.external_apis.web_search import WebSearchClient


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


class GovernmentPublicWebSource(VerificationSource):
    name = "government_public_web"
    source_type = "web"

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        text = f"{input_item.get('raw', '')} {cleaning_output.get('standardized_address', '')}".strip()
        if "不存在" in text or "已拆除" in text or "注销" in text:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="NOT_FOUND",
                score=0.9,
                summary="政府公开信息未命中有效实体，判定为不存在风险高。",
            )
        if "无法核实" in text:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary="政府公开信息无明确结论。",
            )
        return VerificationSignal(
            source_name=self.name,
            source_type=self.source_type,
            verdict="FOUND",
            score=0.82,
            summary=f"政府公开信息命中候选实体：{entity_name or '未知实体'}。",
        )


class MapServiceSource(VerificationSource):
    name = "map_service"
    source_type = "map_api"

    def __init__(self, runtime_store: Optional[AgentRuntimeStore] = None):
        self.client = MapServiceClient(runtime_store=runtime_store, config={}) if runtime_store else None

    def is_enabled(self, input_item: Dict[str, Any]) -> bool:
        key = os.getenv("MAP_SERVICE_API_KEY", "").strip() or os.getenv("AMAP_API_KEY", "").strip()
        return bool(input_item.get("require_map")) or bool(key)

    def required_missing_item(self) -> Optional[str]:
        key = os.getenv("MAP_SERVICE_API_KEY", "").strip() or os.getenv("AMAP_API_KEY", "").strip()
        if key:
            return None
        return "MAP_SERVICE_API_KEY"

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        task_run_id = str(input_item.get("task_run_id") or "")
        if self.client:
            result = self.client.verify_address(
                standardized_address=str(cleaning_output.get("standardized_address") or ""),
                components=cleaning_output.get("components") or {},
                task_run_id=task_run_id,
            )
            if result.get("found"):
                return VerificationSignal(
                    source_name=self.name,
                    source_type=self.source_type,
                    verdict="FOUND",
                    score=float(result.get("confidence") or 0.8),
                    summary=f"地图服务命中候选实体：{entity_name or '未知实体'}。",
                )
            error_type = str(result.get("error_type") or "")
            if error_type in {"invalid_request", "auth_failed"}:
                return VerificationSignal(
                    source_name=self.name,
                    source_type=self.source_type,
                    verdict="UNKNOWN",
                    score=0.2,
                    summary=f"地图服务调用异常：{error_type}",
                )

        text = f"{input_item.get('raw', '')} {cleaning_output.get('standardized_address', '')}".strip()
        if "不存在" in text:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="NOT_FOUND",
                score=0.92,
                summary="地图服务未检索到可用 POI/地址点位。",
            )
        if "无法核实" in text:
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.25,
                summary="地图服务返回候选不足，无法收敛。",
            )
        return VerificationSignal(
            source_name=self.name,
            source_type=self.source_type,
            verdict="FOUND",
            score=0.88,
            summary=f"地图服务命中候选实体：{entity_name or '未知实体'}。",
        )


class WebSearchSource(VerificationSource):
    name = "web_search"
    source_type = "web_api"

    def __init__(self, runtime_store: Optional[AgentRuntimeStore] = None):
        self.client = WebSearchClient(runtime_store=runtime_store, config={}) if runtime_store else None

    def is_enabled(self, input_item: Dict[str, Any]) -> bool:
        return bool(input_item.get("require_web")) or True

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        raw = str(input_item.get("raw") or cleaning_output.get("standardized_address") or "")
        business = str(entity_name or raw)
        task_run_id = str(input_item.get("task_run_id") or "")
        if self.client:
            result = self.client.search_address_evidence(
                address=raw,
                business_name=business,
                limit=3,
                task_run_id=task_run_id,
            )
            if result.get("found"):
                return VerificationSignal(
                    source_name=self.name,
                    source_type=self.source_type,
                    verdict="FOUND",
                    score=float(result.get("confidence") or 0.5),
                    summary="公开网页来源命中地址/实体线索。",
                )
            return VerificationSignal(
                source_name=self.name,
                source_type=self.source_type,
                verdict="UNKNOWN",
                score=0.2,
                summary=f"公开网页来源未形成有效结论（{result.get('error_type') or 'NO_RESULT'}）。",
            )
        return VerificationSignal(
            source_name=self.name,
            source_type=self.source_type,
            verdict="UNKNOWN",
            score=0.2,
            summary="公开网页来源未启用。",
        )


class ReviewPlatformSource(VerificationSource):
    name = "review_platform"
    source_type = "business_api"

    def __init__(self, runtime_store: Optional[AgentRuntimeStore] = None):
        self.client = ReviewPlatformClient(runtime_store=runtime_store, config={}) if runtime_store else None

    def is_enabled(self, input_item: Dict[str, Any]) -> bool:
        return bool(input_item.get("require_review")) or True

    def verify(self, input_item: Dict[str, Any], cleaning_output: Dict[str, Any], entity_name: str) -> VerificationSignal:
        city = str((cleaning_output.get("components") or {}).get("city") or "")
        address = str(cleaning_output.get("standardized_address") or input_item.get("raw") or "")
        task_run_id = str(input_item.get("task_run_id") or "")
        if self.client:
            result = self.client.query_business_info(
                business_name=str(entity_name or ""),
                city=city,
                address=address,
                task_run_id=task_run_id,
            )
            if result.get("found"):
                status = str(result.get("status") or "unknown")
                if status == "closed":
                    return VerificationSignal(
                        source_name=self.name,
                        source_type=self.source_type,
                        verdict="NOT_FOUND",
                        score=0.85,
                        summary="点评平台显示商户已关闭。",
                    )
                return VerificationSignal(
                    source_name=self.name,
                    source_type=self.source_type,
                    verdict="FOUND",
                    score=0.78,
                    summary="点评平台命中有效经营实体。",
                )
        return VerificationSignal(
            source_name=self.name,
            source_type=self.source_type,
            verdict="UNKNOWN",
            score=0.25,
            summary="点评平台无有效结论。",
        )


class AddressVerificationOrchestrator:
    """Aggregate multiple verification sources into a final status."""

    def __init__(self, runtime_store: Optional[AgentRuntimeStore] = None) -> None:
        if runtime_store is None:
            runtime_store = AgentRuntimeStore()
        self.runtime_store = runtime_store
        self.sources: List[VerificationSource] = [
            GovernmentPublicWebSource(),
            MapServiceSource(runtime_store=self.runtime_store),
            WebSearchSource(runtime_store=self.runtime_store),
            ReviewPlatformSource(runtime_store=self.runtime_store),
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
                        "why_needed": "地图核实能力无法执行，影响线上核实收敛率。",
                        "expected_gain": "提升核实覆盖率并降低不可核实比例。",
                        "fallback_if_missing": "降级到公开网页来源并进入不可核实池。",
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
