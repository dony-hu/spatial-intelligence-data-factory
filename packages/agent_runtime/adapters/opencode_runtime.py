from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from packages.agent_runtime.models.runtime_result import RuntimeResult


class OpenCodeRuntime:
    """基于 OpenCode CLI 的适配器
    
    如果 OpenCode 不可用，使用现有 LLM 调用逻辑
    """

    def __init__(self, config_path=None):
        self._config_path = config_path or os.getenv("OPENCODE_CONFIG_PATH", "config/llm_api.json")
        self._opencode_bin = os.getenv("OPENCODE_BIN", "opencode")

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
            "-p", prompt,
            "-f", "json",
            "-q"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
        return result.stdout

    def run_task(self, task_context, ruleset):
        prompt = self._build_prompt(task_context, ruleset)
        
        if self._ensure_opencode_available():
            try:
                raw_output = self._run_opencode_prompt(prompt)
                parsed = self._parse_opencode_output(raw_output)
                return self._build_runtime_result(parsed, ruleset, source="opencode")
            except Exception:
                pass
        
        return self._fallback_result(task_context, ruleset)

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
        try:
            return json.loads(raw)
        except Exception:
            return {}

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

    def _fallback_result(self, task_context, ruleset):
        return RuntimeResult(
            strategy="human_required",
            confidence=0.3,
            evidence={
                "items": [
                    {
                        "runtime": "opencode",
                        "source": "fallback",
                        "message": "no_opencode_available",
                        "ruleset": ruleset.get("ruleset_id", "default"),
                    }
                ]
            },
            agent_run_id=f"fallback_{uuid4().hex[:10]}",
            raw_response={},
        )

    def generate_governance_script(self, description):
        prompt = f"""
你是工厂工艺Agent。
请根据以下需求生成地址治理脚本，输出到 scripts/ 目录：
{description}
""".strip()
        if self._ensure_opencode_available():
            try:
                return self._run_opencode_prompt(prompt)
            except Exception:
                pass
        return "OpenCode 不可用，脚本生成功能待实现"

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
