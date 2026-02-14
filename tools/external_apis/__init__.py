"""Base external API client with caching, error handling, and logging."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None  # type: ignore


class APIErrorType(Enum):
    """API error classification."""

    TIMEOUT = "timeout"
    AUTH_FAILED = "auth_failed"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNKNOWN = "unknown"


class ExternalAPIClient(ABC):
    """Base external API client with caching, error handling, and logging."""

    api_name: str
    timeout_sec: int = 10
    cache_ttl_sec: int = 3600
    max_retries: int = 3

    def __init__(self, runtime_store, config: Optional[Dict[str, Any]] = None):
        self.runtime_store = runtime_store
        self.config = config or {}
        self.logger = self._setup_logger()

    def call(self, request: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Optional[APIErrorType]]:
        """Execute API call with caching and error handling.

        Returns:
            (success, response_data, error_type)
        """
        # Check cache
        cache_key = self._make_cache_key(request)
        cached = self._get_cache(cache_key)
        if cached:
            return True, cached, None

        # Retry loop
        last_error = None
        for attempt in range(self.max_retries):
            t0 = time.time()
            try:
                response = self._call_impl(request)
                latency = int((time.time() - t0) * 1000)
            except (requests.Timeout if requests else TimeoutError) as e:
                last_error = (False, {}, APIErrorType.TIMEOUT, 0)
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
                continue
            except (requests.ConnectionError if requests else Exception) as e:
                last_error = (False, {}, APIErrorType.SERVICE_UNAVAILABLE, 0)
                continue
            except Exception as e:
                error_type = self._classify_error(e)
                self._log_call(request, None, str(e), error_type, 0)
                return False, {}, error_type

            # Validate response
            valid, error_type = self._validate_response(response)
            if not valid:
                self._log_call(request, response, "validation_failed", error_type, latency)
                return False, {}, error_type

            # Cache and return
            self._set_cache(cache_key, response, self.cache_ttl_sec)
            self._log_call(request, response, "success", None, latency)
            return True, response, None

        # All retries failed
        if last_error:
            return last_error
        return False, {}, APIErrorType.UNKNOWN

    @abstractmethod
    def _call_impl(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Actually call the external API - override in subclass."""
        raise NotImplementedError

    @abstractmethod
    def _validate_response(self, response: Dict[str, Any]) -> Tuple[bool, Optional[APIErrorType]]:
        """Validate response structure - override in subclass."""
        return True, None

    def _classify_error(self, exc: Exception) -> APIErrorType:
        """Classify exception type - override in subclass for specific errors."""
        return APIErrorType.SERVICE_UNAVAILABLE

    def _make_cache_key(self, request: Dict[str, Any]) -> str:
        """Generate cache key from request."""
        text = json.dumps(request, sort_keys=True, ensure_ascii=False)
        return f"{self.api_name}:{hashlib.sha256(text.encode()).hexdigest()}"

    def _get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Query external_api_cache table."""
        try:
            with self.runtime_store.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT response_json FROM external_api_cache WHERE cache_key = ? AND expires_at > datetime('now')",
                    (cache_key,),
                )
                row = cursor.fetchone()
                if row:
                    cursor.execute(
                        "UPDATE external_api_cache SET hit_count = hit_count + 1 WHERE cache_key = ?",
                        (cache_key,),
                    )
                    conn.commit()
                    return json.loads(row[0])
        except Exception as e:
            self.logger.warning(f"Cache lookup failed: {e}")
        return None

    def _set_cache(self, cache_key: str, value: Dict[str, Any], ttl: int):
        """Insert into external_api_cache table."""
        try:
            expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
            with self.runtime_store.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO external_api_cache
                       (cache_key, api_name, response_json, cached_at, expires_at, hit_count)
                       VALUES (?, ?, ?, datetime('now'), ?, 0)""",
                    (cache_key, self.api_name, json.dumps(value, ensure_ascii=False), expires_at),
                )
                conn.commit()
        except Exception as e:
            self.logger.warning(f"Cache write failed: {e}")

    def _log_call(self, request: Dict[str, Any], response: Optional[Dict[str, Any]], status: str, error_type: Optional[APIErrorType], latency: int):
        """Insert into api_call_log table."""
        try:
            self.runtime_store.log_api_call(
                api_name=self.api_name,
                request_json=json.dumps(request, ensure_ascii=False),
                response_json=json.dumps(response or {}, ensure_ascii=False),
                error_type=error_type.value if error_type else None,
                latency_ms=latency,
                task_run_id=str(request.get("task_run_id") or "") or None,
            )
        except Exception as e:
            self.logger.warning(f"Call logging failed: {e}")

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"external_api.{self.api_name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            logger.addHandler(handler)
        return logger
