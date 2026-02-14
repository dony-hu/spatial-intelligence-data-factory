"""Map service API client for address verification."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from . import APIErrorType, ExternalAPIClient


class MapServiceClient(ExternalAPIClient):
    """高德地图API客户端 - 地址地理位置验证."""

    api_name = "map_service"

    def __init__(self, runtime_store, config=None):
        super().__init__(runtime_store, config)
        self.api_key = (
            os.getenv("AMAP_API_KEY", "").strip()
            or os.getenv("MAP_SERVICE_API_KEY", "").strip()
        )
        self.endpoint = (
            config.get("endpoint", "https://restapi.amap.com/v3/geocode/geo")
            if config
            else "https://restapi.amap.com/v3/geocode/geo"
        )

    def verify_address(
        self,
        standardized_address: str,
        components: Dict[str, str],
        task_run_id: str = "",
    ) -> Dict[str, Any]:
        """Verify standardized address using Amap API.

        Args:
            standardized_address: e.g., "北京市朝阳区建国路1号"
            components: { "province": "北京市", "city": "朝阳区", ... }

        Returns:
            {
                "found": bool,
                "confidence": 0.0-1.0,
                "location": "116.123456,39.123456",
                "address": "完整地址",
                "verification_source": "map_service",
                "error_type": null or error
            }
        """
        request = {
            "address": standardized_address,
            "city": components.get("city", ""),
            "key": self.api_key,
            "task_run_id": task_run_id,
        }

        success, response, error = self.call(request)

        if not success:
            return {
                "found": False,
                "confidence": 0.0,
                "error_type": error.value if error else "unknown",
                "verification_source": self.api_name,
                "candidates": [],
            }

        # Parse Amap response
        if response.get("status") == "1":  # Success
            results = response.get("geocodes", [])
            if results:
                best = results[0]
                return {
                    "found": True,
                    "confidence": 0.88,
                    "location": best.get("location", ""),
                    "address": best.get("formatted_address", ""),
                    "province": best.get("province", ""),
                    "city": best.get("city", ""),
                    "district": best.get("district", ""),
                    "verification_source": self.api_name,
                    "candidates": results[:3],
                }

        return {
            "found": False,
            "confidence": 0.0,
            "error_type": None,
            "verification_source": self.api_name,
            "candidates": [],
        }

    def _call_impl(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call Amap geocoding API."""
        if not requests:
            raise ImportError("requests library is required for API calls")

        payload = {k: v for k, v in request.items() if k != "key"}
        payload["key"] = self.api_key

        response = requests.get(self.endpoint, params=payload, timeout=self.timeout_sec)
        response.raise_for_status()
        return response.json()

    def _validate_response(self, response: Dict[str, Any]) -> Tuple[bool, Optional[APIErrorType]]:
        """Validate Amap response structure."""
        status = response.get("status")
        if status == "1":
            return True, None
        if status == "0":
            return False, APIErrorType.INVALID_REQUEST
        if status == "2":
            return False, APIErrorType.AUTH_FAILED
        return False, APIErrorType.SERVICE_UNAVAILABLE
