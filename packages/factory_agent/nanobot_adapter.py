from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from nanobot.providers.custom_provider import CustomProvider


class NanobotAdapter:
    """FactoryAgent -> nanobot 统一适配层（无 fallback）。"""

    def __init__(self, *, config_path: str | Path = "config/llm_api.json") -> None:
        raw_path = Path(config_path)
        if raw_path.is_absolute():
            self._config_path = raw_path
        else:
            cwd_candidate = Path.cwd() / raw_path
            repo_candidate = Path(__file__).resolve().parents[2] / raw_path
            self._config_path = cwd_candidate if cwd_candidate.exists() else repo_candidate
        self._settings = self._load_settings()
        self._provider = CustomProvider(
            api_key=self._settings["api_key"],
            api_base=self._settings["base_url"],
            default_model=self._settings["model"],
        )

    def chat(
        self,
        prompt: str,
        *,
        system_prompt: str = "",
        session_key: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Dict[str, Any]:
        return self._query(
            prompt,
            system_prompt=system_prompt,
            session_key=session_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def query_structured(
        self,
        requirement: str,
        *,
        system_prompt: str = "",
        session_key: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Dict[str, Any]:
        return self._query(
            requirement,
            system_prompt=system_prompt,
            session_key=session_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _query(
        self,
        user_text: str,
        *,
        system_prompt: str,
        session_key: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> Dict[str, Any]:
        request_messages = [
            {"role": "system", "content": str(system_prompt or "").strip() or "你是数据治理工厂助手。"},
            {"role": "user", "content": str(user_text or "").strip()},
        ]
        if not str(request_messages[1]["content"]).strip():
            raise RuntimeError("nanobot request content is empty")

        timeout_sec = int(self._settings["timeout_sec"])
        request_model = self._settings["model"]
        request_temp = float(self._settings["temperature"] if temperature is None else temperature)
        request_tokens = int(self._settings["max_tokens"] if max_tokens is None else max_tokens)

        started = perf_counter()

        async def _call_provider():
            return await asyncio.wait_for(
                self._provider.chat(
                    messages=request_messages,
                    model=request_model,
                    temperature=request_temp,
                    max_tokens=request_tokens,
                ),
                timeout=timeout_sec,
            )

        response = self._run_coroutine(_call_provider())
        latency_ms = round((perf_counter() - started) * 1000, 3)
        answer = str(response.content or "").strip()
        if response.finish_reason == "error":
            raise RuntimeError(answer or "nanobot provider returned error finish_reason")
        if not answer:
            raise RuntimeError("nanobot response is empty")

        usage = response.usage or {}
        token_usage = {
            "prompt": int(usage.get("prompt_tokens") or 0),
            "completion": int(usage.get("completion_tokens") or 0),
            "total": int(usage.get("total_tokens") or 0),
        }
        return {
            "status": "ok",
            "answer": answer,
            "latency_ms": latency_ms,
            "token_usage": token_usage,
            "request": {
                "model": request_model,
                "messages": request_messages,
                "temperature": request_temp,
                "max_tokens": request_tokens,
                "session_key": str(session_key or "").strip(),
                "provider": "nanobot.custom_provider",
                "base_url": self._settings["base_url"],
            },
            "raw": {
                "finish_reason": str(response.finish_reason or ""),
                "tool_calls_count": int(len(response.tool_calls or [])),
                "reasoning_content": str(response.reasoning_content or ""),
            },
        }

    def _load_settings(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if self._config_path.exists():
            try:
                loaded = json.loads(self._config_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payload = loaded
            except Exception as exc:
                raise RuntimeError(f"nanobot config parse failed: {exc}") from exc

        endpoint = str(payload.get("endpoint") or os.getenv("LLM_ENDPOINT") or "").strip()
        base_url = str(payload.get("base_url") or os.getenv("LLM_BASE_URL") or "").strip()
        model = str(payload.get("model") or os.getenv("LLM_MODEL") or "").strip()
        api_key = str(payload.get("api_key") or os.getenv("LLM_API_KEY") or "").strip()
        timeout_sec = int(payload.get("timeout_sec") or os.getenv("LLM_TIMEOUT_SEC") or 60)
        temperature = float(payload.get("temperature") or os.getenv("LLM_TEMPERATURE") or 0.2)
        max_tokens = int(payload.get("max_tokens") or os.getenv("LLM_MAX_TOKENS") or 1200)

        resolved_base_url = self._resolve_base_url(endpoint=endpoint, base_url=base_url)
        if not model:
            raise RuntimeError("nanobot config missing model")
        if not api_key:
            raise RuntimeError("nanobot config missing api_key")

        return {
            "base_url": resolved_base_url,
            "model": model,
            "api_key": api_key,
            "timeout_sec": timeout_sec,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _resolve_base_url(self, *, endpoint: str, base_url: str) -> str:
        value = str(base_url or "").strip() or str(endpoint or "").strip()
        if not value:
            raise RuntimeError("nanobot config missing endpoint/base_url")
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise RuntimeError(f"nanobot invalid endpoint/base_url: {value}")

        path = str(parsed.path or "")
        lowered = path.lower()
        for suffix in ("/chat/completions", "/responses"):
            if lowered.endswith(suffix):
                path = path[: -len(suffix)]
                lowered = path.lower()
                break
        if not path:
            path = "/v1"
        normalized = f"{parsed.scheme}://{parsed.netloc}{path.rstrip('/')}"
        if not normalized.endswith("/v1"):
            if "/v1/" in lowered:
                normalized = f"{parsed.scheme}://{parsed.netloc}{path[:lowered.find('/v1/') + 3]}"
            elif lowered != "/v1":
                normalized = normalized + "/v1"
        return normalized

    def _run_coroutine(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        bucket: Dict[str, Any] = {}

        def _target() -> None:
            try:
                bucket["result"] = asyncio.run(coro)
            except Exception as exc:  # pragma: no cover - only in nested-loop environments
                bucket["error"] = exc

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join()
        if "error" in bucket:
            raise bucket["error"]
        return bucket.get("result")
