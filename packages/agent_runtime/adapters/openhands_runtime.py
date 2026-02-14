from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from packages.agent_runtime.models.runtime_result import RuntimeResult


class OpenHandsRuntime:
    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config_path = config_path or os.getenv("LLM_CONFIG_PATH", "config/llm_api.json")

    def _load_llm_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {
            "provider": "openai_compatible",
            "endpoint": os.getenv("LLM_ENDPOINT", "https://ark.cn-beijing.volces.com/api/v3/chat/completions"),
            "model": os.getenv("LLM_MODEL", "doubao-seed-2-0-mini-260215"),
            "api_key": os.getenv("LLM_API_KEY", ""),
            "timeout_sec": 60,
            "temperature": 0.2,
            "max_tokens": 600,
        }
        path = Path(self._config_path)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    config.update(data)
            except Exception:
                pass
        return config

    def _build_messages(self, task_context: dict, ruleset: dict) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "你是地址治理执行Agent。"
                    "请根据输入地址给出治理建议，并输出JSON对象，字段: "
                    "strategy, confidence, canonical, actions, evidence。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task_context": task_context,
                        "ruleset": ruleset,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def _post_chat_completion(self, config: Dict[str, Any], messages: list[dict[str, str]]) -> Dict[str, Any]:
        payload = {
            "model": str(config.get("model") or "doubao-seed-2-0-mini-260215"),
            "messages": messages,
            "temperature": float(config.get("temperature", 0.2)),
            "max_tokens": int(config.get("max_tokens", 600)),
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {str(config.get('api_key') or '')}",
        }
        request = Request(
            str(config.get("endpoint") or ""),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        timeout_sec = float(config.get("timeout_sec", 60))
        with urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("invalid llm response")
        return data

    @staticmethod
    def _extract_text(response_json: Dict[str, Any]) -> str:
        choices = response_json.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""
        message = first.get("message")
        if not isinstance(message, dict):
            return ""
        return str(message.get("content") or "")

    @staticmethod
    def _parse_json_like(content: str) -> Dict[str, Any]:
        text = str(content or "").strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                candidate = part.strip()
                if candidate.lower().startswith("json"):
                    candidate = candidate[4:].strip()
                if not candidate:
                    continue
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    continue
        return {}

    def _fallback_result(self, ruleset: dict, reason: str) -> RuntimeResult:
        return RuntimeResult(
            strategy="human_required",
            confidence=0.5,
            evidence={
                "items": [
                    {
                        "runtime": "openhands",
                        "message": "llm_call_fallback",
                        "reason": reason,
                        "ruleset": ruleset.get("ruleset_id", "default"),
                    }
                ]
            },
            agent_run_id=f"openhands_{uuid4().hex[:10]}",
            raw_response={"fallback": True, "reason": reason},
        )

    def _strict_mode(self) -> bool:
        return os.getenv("OPENHANDS_STRICT", "1") == "1"

    def run_task(self, task_context: dict, ruleset: dict) -> RuntimeResult:
        config = self._load_llm_config()
        api_key = str(config.get("api_key") or "")
        endpoint = str(config.get("endpoint") or "")
        if not endpoint or not api_key:
            if self._strict_mode():
                raise RuntimeError("missing_endpoint_or_api_key")
            return self._fallback_result(ruleset, "missing_endpoint_or_api_key")

        messages = self._build_messages(task_context, ruleset)
        try:
            response_json = self._post_chat_completion(config, messages)
            content = self._extract_text(response_json)
            parsed = self._parse_json_like(content)

            strategy = str(parsed.get("strategy") or "human_required")
            confidence = float(parsed.get("confidence") or 0.5)
            canonical = parsed.get("canonical") if isinstance(parsed.get("canonical"), dict) else {}
            raw_actions = parsed.get("actions") if isinstance(parsed.get("actions"), list) else []
            actions = []
            for action in raw_actions:
                if isinstance(action, dict):
                    actions.append(action)
                else:
                    actions.append({"value": str(action)})

            evidence = parsed.get("evidence") if isinstance(parsed.get("evidence"), dict) else {"items": []}
            raw_items = evidence.get("items") if isinstance(evidence.get("items"), list) else []
            evidence_items = []
            for item in raw_items:
                if isinstance(item, dict):
                    evidence_items.append(item)
                else:
                    evidence_items.append({"value": str(item)})
            evidence_items.append(
                {
                    "runtime": "openhands",
                    "message": "llm_call_success",
                    "ruleset": ruleset.get("ruleset_id", "default"),
                    "model": str(config.get("model") or ""),
                }
            )
            evidence = {"items": evidence_items}
            response_id = str(response_json.get("id") or "")
            agent_run_id = response_id if response_id else f"openhands_{uuid4().hex[:10]}"

            return RuntimeResult(
                strategy=strategy,
                canonical=canonical,
                confidence=max(0.0, min(1.0, confidence)),
                evidence=evidence,
                actions=actions,
                agent_run_id=agent_run_id,
                raw_response={
                    "id": response_json.get("id"),
                    "model": response_json.get("model"),
                    "usage": response_json.get("usage"),
                    "has_content": bool(content),
                },
            )
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            if self._strict_mode():
                raise
            return self._fallback_result(ruleset, exc.__class__.__name__)
        except Exception as exc:
            if self._strict_mode():
                raise
            return self._fallback_result(ruleset, exc.__class__.__name__)
