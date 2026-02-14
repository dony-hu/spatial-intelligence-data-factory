"""Review platform API client for business verification."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from . import APIErrorType, ExternalAPIClient


class ReviewPlatformClient(ExternalAPIClient):
    """点评平台API客户端 - 验证商户信息和经营状态."""

    api_name = "review_platform"

    def __init__(self, runtime_store, config=None):
        super().__init__(runtime_store, config)
        self.endpoint = config.get("endpoint", "") if config else ""
        self.api_key = config.get("api_key", "") if config else ""

    def query_business_info(self, business_name: str, city: str, address: str) -> Dict[str, Any]:
        """Query business info (status, rating, etc.) from review platform.

        Returns:
            {
                "found": bool,
                "business_id": str,
                "rating": 0.0-5.0,
                "review_count": int,
                "status": "operating" | "closed" | "relocated" | "unknown",
                "verified_at": timestamp,
                "verification_source": "review_platform"
            }
        """
        request = {
            "business_name": business_name,
            "city": city,
            "address": address,
            "fields": ["rating", "review_count", "status", "verified_time"],
        }

        success, response, error = self.call(request)

        if not success:
            return {
                "found": False,
                "error_type": error.value if error else "unknown",
                "verification_source": self.api_name,
            }

        # Parse response
        if response.get("results"):
            result = response["results"][0]
            return {
                "found": True,
                "business_id": result.get("id"),
                "rating": float(result.get("rating", 0)),
                "review_count": int(result.get("review_count", 0)),
                "status": result.get("status", "unknown"),
                "verified_at": result.get("verified_time"),
                "verification_source": self.api_name,
            }

        return {"found": False, "verification_source": self.api_name}

    def _call_impl(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call review platform API (placeholder)."""
        raise NotImplementedError("Configure review_platform endpoint first")

    def _validate_response(self, response: Dict[str, Any]) -> Tuple[bool, Optional[APIErrorType]]:
        """Validate response structure."""
        return True, None
