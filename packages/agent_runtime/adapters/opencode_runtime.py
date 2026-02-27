from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from packages.agent_runtime.models.runtime_result import RuntimeResult


class OpenCodeRuntime:
    """基于 OpenCode CLI 的适配器（严格模式，无 fallback）。"""

    def __init__(self, config_path=None):
        self._config_path = config_path or os.getenv("OPENCODE_CONFIG_PATH", "config/llm_api.json")
        self._opencode_bin = os.getenv("OPENCODE_BIN", "opencode")
        self._timeout_sec = int(os.getenv("OPENCODE_TIMEOUT_SEC", "300"))

    def _ensure_opencode_available(self):
        try:
            subprocess.run([self._opencode_bin, "--version"],
                           capture_output=True, check=True, timeout=10)
            return True
        except Exception:
            return False

    def _run_opencode_prompt(self, prompt):
        cmd = [
            self._opencode_bin,
            "run",
            prompt,
            "--format",
            "json",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=self._timeout_sec,
        )
        return result.stdout

    def run_task(self, task_context, ruleset):
        prompt = self._build_prompt(task_context, ruleset)

        if not self._ensure_opencode_available():
            raise RuntimeError("blocked: opencode unavailable")
        try:
            raw_output = self._run_opencode_prompt(prompt)
            parsed = self._parse_opencode_output(raw_output)
            self._validate_llm_output(parsed)
            return self._build_runtime_result(parsed, ruleset, source="opencode")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"blocked: opencode call failed: {exc}") from exc

    def _build_prompt(self, task_context, ruleset):
        return f"""
你是地址治理执行Agent。

请根据输入地址给出治理建议，并输出JSON对象，字段:
strategy, confidence, canonical, actions, evidence。

输入：
task_context: {json.dumps(task_context, ensure_ascii=False)}
ruleset: {json.dumps(ruleset, ensure_ascii=False)}
""".strip()

    def _parse_opencode_output(self, raw):
        raw_text = raw.strip()
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                if "strategy" in parsed and "confidence" in parsed:
                    return parsed
                embedded = self._extract_json_from_event(parsed)
                if embedded is not None:
                    return embedded
            raise RuntimeError("blocked: opencode output must be a json object")
        except json.JSONDecodeError:
            pass
        except RuntimeError:
            raise

        event_objects = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception as exc:
                raise RuntimeError(f"blocked: opencode output contains invalid json line: {exc}") from exc
            if not isinstance(event, dict):
                raise RuntimeError("blocked: opencode event output must be json objects")
            event_objects.append(event)

        for event in reversed(event_objects):
            embedded = self._extract_json_from_event(event)
            if embedded is not None:
                return embedded
        raise RuntimeError("blocked: opencode output missing structured json payload")

    def _extract_json_from_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        text_candidates = []
        part = event.get("part")
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str):
                text_candidates.append(text.strip())
        message = event.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                text_candidates.append(content.strip())

        for text in text_candidates:
            payload = self._extract_json_payload_text(text)
            if not payload:
                continue
            try:
                parsed = json.loads(payload)
            except Exception:
                continue
            if isinstance(parsed, dict) and "strategy" in parsed and "confidence" in parsed:
                return parsed
        return None

    def _extract_json_payload_text(self, text: str) -> Optional[str]:
        stripped = text.strip()
        if not stripped:
            return None
        if stripped.startswith("```"):
            first_newline = stripped.find("\n")
            if first_newline >= 0:
                stripped = stripped[first_newline + 1:]
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return stripped[start : end + 1]
        return None

    def _validate_llm_output(self, parsed: Dict[str, Any]) -> None:
        if not isinstance(parsed, dict):
            raise RuntimeError("blocked: opencode output must be a json object")
        missing = []
        for key in ("strategy", "confidence"):
            if key not in parsed:
                missing.append(key)
        if missing:
            raise RuntimeError(f"blocked: opencode output missing fields: {','.join(missing)}")

    def _build_runtime_result(self, parsed, ruleset, source="unknown"):
        strategy = str(parsed.get("strategy", "human_required"))
        confidence = float(parsed.get("confidence", 0.5))
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
                "runtime": "opencode",
                "source": source,
                "message": "llm_call_success",
                "ruleset": ruleset.get("ruleset_id", "default")
            }
        )
        evidence = {"items": evidence_items}
        agent_run_id = f"opencode_{uuid4().hex[:10]}"
        return RuntimeResult(
            strategy=strategy,
            canonical=canonical,
            confidence=max(0.0, min(1.0, confidence)),
            evidence=evidence,
            actions=actions,
            agent_run_id=agent_run_id,
            raw_response=parsed,
        )

    def generate_governance_script(self, description):
        prompt = f"""
你是工厂工艺Agent。
请根据以下需求生成地址治理脚本，输出到 scripts/ 目录：
{description}
""".strip()
        if not self._ensure_opencode_available():
            raise RuntimeError("blocked: opencode unavailable")
        try:
            return self._run_opencode_prompt(prompt)
        except Exception as exc:
            raise RuntimeError(f"blocked: script generation failed: {exc}") from exc

    def supplement_trust_hub_data(self, source):
        return {
            "status": "pending",
            "source": source,
            "message": "可信数据 HUB 补充功能待实现"
        }

    def output_skill_package(self, skill_name, skill_spec):
        from packages.factory_agent.agent import FactoryAgent
        agent = FactoryAgent()
        result = agent.output_skill(skill_name, skill_spec)
        return Path(result["skill_path"])
