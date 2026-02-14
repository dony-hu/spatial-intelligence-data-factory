"""LLM client helpers for process expert agent workflows."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG_PATH = "config/llm_api.json"


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load LLM config from file with env fallback.

    Required final fields:
    - provider
    - endpoint
    - model
    - api_key
    """
    config: Dict[str, Any] = {}
    path = Path(config_path)
    if path.exists():
        config = json.loads(path.read_text(encoding="utf-8"))

    provider = str(config.get("provider") or os.getenv("LLM_PROVIDER") or "openai_compatible")
    endpoint = str(
        config.get("endpoint")
        or os.getenv("LLM_ENDPOINT")
        or "https://api.openai.com/v1/chat/completions"
    )
    model = str(config.get("model") or os.getenv("LLM_MODEL") or "")
    api_key = str(config.get("api_key") or os.getenv("LLM_API_KEY") or "")
    timeout_sec = int(config.get("timeout_sec") or os.getenv("LLM_TIMEOUT_SEC") or 60)
    temperature = float(config.get("temperature") or os.getenv("LLM_TEMPERATURE") or 0.2)
    max_tokens = int(config.get("max_tokens") or os.getenv("LLM_MAX_TOKENS") or 1200)

    merged = {
        "provider": provider,
        "endpoint": endpoint,
        "model": model,
        "api_key": api_key,
        "timeout_sec": timeout_sec,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if not merged["model"]:
        raise RuntimeError("LLM model is missing. Set config.model or env LLM_MODEL")
    if not merged["api_key"]:
        raise RuntimeError("LLM api_key is missing. Set config.api_key or env LLM_API_KEY")

    return merged


def run_requirement_query(
    requirement: str,
    config: Dict[str, Any],
    system_prompt_override: str = "",
) -> Dict[str, Any]:
    """Run one chat completion call for process expert planning."""
    system_prompt = (
        system_prompt_override.strip()
        or "你是工艺专家Agent，请输出可执行的工艺方案，并尽量返回JSON代码块。"
    )

    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": requirement},
        ],
        "temperature": float(config.get("temperature", 0.2)),
        "max_tokens": int(config.get("max_tokens", 1200)),
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=str(config["endpoint"]),
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=int(config.get("timeout_sec", 60))) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore") if hasattr(exc, "read") else str(exc)
        raise RuntimeError(f"LLM HTTP error: {exc.code} {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError("LLM response missing choices")

    message = choices[0].get("message") or {}
    answer = str(message.get("content") or "").strip()
    if not answer:
        raise RuntimeError("LLM response content is empty")

    return {
        "status": "ok",
        "answer": answer,
        "raw": parsed,
    }


def parse_plan_from_answer(answer: str) -> Dict[str, Any]:
    """Parse JSON object from LLM answer and normalize planning keys."""
    raw = str(answer or "").strip()
    obj = _extract_json_dict(raw) or {}

    return {
        "auto_execute": _to_bool(obj.get("auto_execute", False)),
        "max_duration": _to_int(obj.get("max_duration"), 1200),
        "quality_threshold": _to_float(obj.get("quality_threshold"), 0.9),
        "priority": _to_int(obj.get("priority"), 1),
        "addresses": obj.get("addresses", []) if isinstance(obj.get("addresses"), list) else [],
    }


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "y", "on", "是", "开启"}:
            return True
        if text in {"false", "0", "no", "n", "off", "否", "关闭"}:
            return False
    return default


def _to_int(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            m = re.search(r"-?\d+", text)
            if m:
                try:
                    return int(m.group(0))
                except Exception:
                    pass
    return default


def _to_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            m = re.search(r"-?\d+(?:\.\d+)?", text)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    pass
    return default


def _extract_json_dict(text: str) -> Dict[str, Any] | None:
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1))
    braced = re.search(r"(\{[\s\S]*\})", text)
    if braced:
        candidates.append(braced.group(1))

    for item in candidates:
        try:
            parsed = json.loads(item)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue
    return None
