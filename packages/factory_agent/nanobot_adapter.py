from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
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
        timeout_sec: int | None = None,
    ) -> Dict[str, Any]:
        return self._query(
            prompt,
            system_prompt=system_prompt,
            session_key=session_key,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_sec=timeout_sec,
        )

    def query_structured(
        self,
        requirement: str,
        *,
        system_prompt: str = "",
        session_key: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_sec: int | None = None,
    ) -> Dict[str, Any]:
        return self._query(
            requirement,
            system_prompt=system_prompt,
            session_key=session_key,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_sec=timeout_sec,
        )

    def _query(
        self,
        user_text: str,
        *,
        system_prompt: str,
        session_key: str | None,
        max_tokens: int | None,
        temperature: float | None,
        timeout_sec: int | None,
    ) -> Dict[str, Any]:
        request_messages = [
            {"role": "system", "content": str(system_prompt or "").strip() or "你是数据治理工厂助手。"},
            {"role": "user", "content": str(user_text or "").strip()},
        ]
        if not str(request_messages[1]["content"]).strip():
            raise RuntimeError("nanobot request content is empty")

        request_timeout_sec = int(self._settings["timeout_sec"] if timeout_sec is None else timeout_sec)
        request_model = self._settings["model"]
        request_temp = float(self._settings["temperature"] if temperature is None else temperature)
        request_tokens = int(self._settings["max_tokens"] if max_tokens is None else max_tokens)

        started = perf_counter()
        transport = str(self._settings.get("transport") or "sdk").strip().lower()

        if transport == "curl":
            response = self._query_via_curl(
                request_messages,
                model=request_model,
                temperature=request_temp,
                max_tokens=request_tokens,
                timeout_sec=request_timeout_sec,
            )
            latency_ms = round((perf_counter() - started) * 1000, 3)
            answer = str(response.get("content") or "").strip()
            if not answer:
                raise RuntimeError("nanobot response is empty")
            token_usage = {
                "prompt": int(response.get("prompt_tokens") or 0),
                "completion": int(response.get("completion_tokens") or 0),
                "total": int(response.get("total_tokens") or 0),
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
                    "timeout_sec": request_timeout_sec,
                    "session_key": str(session_key or "").strip(),
                    "provider": "nanobot.curl_provider",
                    "base_url": self._settings["base_url"],
                    "endpoint": self._settings["endpoint"],
                },
                "raw": {
                    "finish_reason": str(response.get("finish_reason") or ""),
                    "tool_calls_count": 0,
                    "reasoning_content": str(response.get("reasoning_content") or ""),
                },
            }

        async def _call_provider():
            return await asyncio.wait_for(
                self._provider.chat(
                    messages=request_messages,
                    model=request_model,
                    temperature=request_temp,
                    max_tokens=request_tokens,
                ),
                timeout=request_timeout_sec,
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
                "timeout_sec": request_timeout_sec,
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

    def _query_via_curl(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_sec: int,
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max(1, int(max_tokens)),
        }
        cmd = [
            "curl",
            "-sS",
            "-m",
            str(max(1, int(timeout_sec))),
            "-X",
            "POST",
            str(self._settings["endpoint"]),
            "-H",
            f"Authorization: Bearer {self._settings['api_key']}",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload, ensure_ascii=False),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=max(1, int(timeout_sec)) + 5,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"curl llm request process timeout: {exc}") from exc
        if int(proc.returncode) != 0:
            err = str(proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"curl llm request failed rc={int(proc.returncode)}: {err}")
        raw_text = str(proc.stdout or "").strip()
        if not raw_text:
            raise RuntimeError("curl llm response is empty")
        try:
            body = json.loads(raw_text)
        except Exception as exc:
            raise RuntimeError(f"curl llm response parse failed: {exc}") from exc

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("curl llm response missing choices")
        first = choices[0] if isinstance(choices[0], dict) else {}
        msg = first.get("message") if isinstance(first.get("message"), dict) else {}
        content = str(msg.get("content") or "").strip()
        if not content:
            raise RuntimeError("curl llm response content is empty")
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        return {
            "content": content,
            "finish_reason": str(first.get("finish_reason") or ""),
            "reasoning_content": str(msg.get("reasoning_content") or ""),
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
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

        endpoint = self._resolve_config_value(payload.get("endpoint"), env_name="LLM_ENDPOINT")
        base_url = self._resolve_config_value(payload.get("base_url"), env_name="LLM_BASE_URL")
        model = self._resolve_config_value(payload.get("model"), env_name="LLM_MODEL")
        api_key = self._resolve_config_value(payload.get("api_key"), env_name="LLM_API_KEY")
        timeout_sec = int(payload.get("timeout_sec") or os.getenv("LLM_TIMEOUT_SEC") or 60)
        temperature = float(payload.get("temperature") or os.getenv("LLM_TEMPERATURE") or 0.2)
        max_tokens = int(payload.get("max_tokens") or os.getenv("LLM_MAX_TOKENS") or 1200)
        provider = str(payload.get("provider") or "openai_compatible").strip().lower()
        transport = self._resolve_config_value(payload.get("transport"), env_name="LLM_TRANSPORT").lower()

        resolved_base_url = self._resolve_base_url(endpoint=endpoint, base_url=base_url)
        if not model:
            raise RuntimeError("nanobot config missing model")
        if not api_key:
            raise RuntimeError("nanobot config missing api_key (LLM_API_KEY unresolved)")
        if not transport:
            transport = "curl" if provider == "openai_compatible" else "sdk"

        resolved_endpoint = str(endpoint or "").strip()
        if not resolved_endpoint:
            resolved_endpoint = resolved_base_url.rstrip("/") + "/chat/completions"

        return {
            "endpoint": resolved_endpoint,
            "base_url": resolved_base_url,
            "model": model,
            "api_key": api_key,
            "timeout_sec": timeout_sec,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "provider": provider,
            "transport": transport,
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

    def _resolve_config_value(self, raw: Any, *, env_name: str) -> str:
        value = str(raw or "").strip()
        if value:
            # 支持 config 中 `${ENV_VAR}` 占位符写法。
            matched = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value)
            if matched:
                return str(os.getenv(matched.group(1)) or "").strip()
            return value
        return str(os.getenv(env_name) or "").strip()

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
