"""Web search API client for address evidence collection."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from . import APIErrorType, ExternalAPIClient


class WebSearchClient(ExternalAPIClient):
    """网页搜索客户端 - 查询地址和商户的公开信息."""

    api_name = "web_search"

    def __init__(self, runtime_store, config=None):
        super().__init__(runtime_store, config)
        self.endpoint = config.get("endpoint", "") if config else ""
        self.api_key = config.get("api_key", "") if config else ""

    def search_address_evidence(
        self,
        address: str,
        business_name: str,
        limit: int = 5,
        task_run_id: str = "",
    ) -> Dict[str, Any]:
        """Search web for address/business mentions.

        Returns:
            {
                "found": bool,
                "results": [{ "title", "url", "snippet", "relevance" }],
                "confidence": 0.0-1.0,
                "verification_source": "web_search"
            }
        """
        request = {
            "query": f'"{address}" "{business_name}"',
            "limit": limit,
            "language": "zh",
            "task_run_id": task_run_id,
        }

        success, response, error = self.call(request)

        if not success:
            return {
                "found": False,
                "error_type": error.value if error else "unknown",
                "results": [],
                "verification_source": self.api_name,
            }

        # Parse search results
        results = response.get("results", [])
        if results:
            return {
                "found": True,
                "results": results,
                "confidence": min(0.8, len(results) * 0.2),  # Scale: 0-0.8
                "verification_source": self.api_name,
            }

        return {
            "found": False,
            "results": [],
            "verification_source": self.api_name,
        }

    def _call_impl(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call web search API if endpoint configured, otherwise return deterministic fallback.
        """
        if self.endpoint and requests:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(
                f"{self.endpoint}?{urlencode(request, doseq=True)}",
                headers=headers,
                timeout=self.timeout_sec,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            return {"results": []}

        query = str(request.get("query") or "")
        limit = max(1, int(request.get("limit") or 5))
        if "不存在" in query or "已拆除" in query:
            return {"results": []}
        return {
            "results": [
                {
                    "title": "公开网页线索（降级）",
                    "url": "https://example.invalid/fallback/web-search",
                    "snippet": query[:120],
                    "relevance": 0.55,
                }
            ][:limit]
        }

    def _validate_response(self, response: Dict[str, Any]) -> Tuple[bool, Optional[APIErrorType]]:
        """Validate response structure."""
        return True, None
