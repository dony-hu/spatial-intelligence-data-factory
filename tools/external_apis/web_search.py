"""Web search API client for address evidence collection."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from . import APIErrorType, ExternalAPIClient


class WebSearchClient(ExternalAPIClient):
    """网页搜索客户端 - 查询地址和商户的公开信息."""

    api_name = "web_search"

    def __init__(self, runtime_store, config=None):
        super().__init__(runtime_store, config)
        self.endpoint = config.get("endpoint", "") if config else ""
        self.api_key = config.get("api_key", "") if config else ""

    def search_address_evidence(self, address: str, business_name: str, limit: int = 5) -> Dict[str, Any]:
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
        """Call web search API (placeholder)."""
        raise NotImplementedError("Configure web_search endpoint first")

    def _validate_response(self, response: Dict[str, Any]) -> Tuple[bool, Optional[APIErrorType]]:
        """Validate response structure."""
        return True, None
