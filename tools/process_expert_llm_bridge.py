from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List

from tools.agent_cli import load_config, parse_plan_from_answer, run_requirement_query
from tools.process_expert_bootstrap import ProcessExpertLLMBridge


class RealProcessExpertLLMBridge(ProcessExpertLLMBridge):
    def __init__(self, config_path: str) -> None:
        self.config = load_config(config_path)
        self.history: List[Dict[str, str]] = []
        self.trace_events: List[Dict[str, Any]] = []

    def _append_trace(self, event_type: str, payload: Dict[str, Any]) -> None:
        self.trace_events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                **payload,
            }
        )

    def pop_trace_events(self) -> List[Dict[str, Any]]:
        items = list(self.trace_events)
        self.trace_events.clear()
        return items

    def generate_plan(self, requirement: str) -> Dict[str, Any]:
        self.history.append({"role": "user", "content": requirement})
        prompt = (
            "你是工艺Agent的规划器。"
            "请输出JSON计划字段: auto_execute,max_duration,quality_threshold,priority,steps。\n"
            f"历史轮次: {json.dumps(self.history[-6:], ensure_ascii=False)}"
        )
        result = run_requirement_query(requirement=prompt, config=self.config)
        answer = str(result.get("answer") or "")
        self.history.append({"role": "assistant", "content": answer})
        plan = parse_plan_from_answer(answer)

        normalized = {
            "auto_execute": bool(plan.get("auto_execute", False)),
            "max_duration_sec": int(plan.get("max_duration") or 300),
            "quality_threshold": float(plan.get("quality_threshold") or 0.8),
            "priority": str(plan.get("priority") or "normal"),
            "steps": plan.get("steps") if isinstance(plan.get("steps"), list) else [
                "地图API采样",
                "LLM归并别名",
                "工具包脚本生成",
                "质量审计回放",
            ],
        }
        self._append_trace(
            "generate_plan",
            {
                "input_requirement": requirement,
                "llm_prompt": prompt,
                "llm_answer": answer,
                "normalized_plan": normalized,
            },
        )
        return {"plan": normalized}

    def suggest_change_request(self, round_index: int, audit: Dict[str, Any], last_result: Dict[str, Any]) -> str:
        audit_gaps = list(audit.get("audit_gaps") or [])
        capability_index = dict(audit.get("trusted_interface_capabilities") or {})
        interface_plan = dict(audit.get("suggested_interface_plan") or {})
        evidence_template = list(audit.get("evidence_checklist_template") or [])
        prompt = (
            "你是工艺迭代器。请根据审计失败项输出一句简洁的change_request。\n"
            "要求: 结合可信数据源接口能力，优先修复P0/P1缺口，并明确证据清单与结论段。\n"
            f"轮次: {round_index}\n"
            f"审计: {json.dumps(audit, ensure_ascii=False)}\n"
            f"结构化缺口: {json.dumps(audit_gaps, ensure_ascii=False)}\n"
            f"可信接口能力索引: {json.dumps(capability_index, ensure_ascii=False)}\n"
            f"建议接口组合: {json.dumps(interface_plan, ensure_ascii=False)}\n"
            f"证据清单模板: {json.dumps(evidence_template, ensure_ascii=False)}\n"
            f"上一轮工艺摘要: process_code={last_result.get('process_code')}"
        )
        result = run_requirement_query(requirement=prompt, config=self.config)
        answer = str(result.get("answer") or "").strip()
        final_change_request = self._extract_change_request(answer, audit)
        self._append_trace(
            "suggest_change_request",
            {
                "round_index": round_index,
                "input_audit": audit,
                "input_audit_gaps": audit_gaps,
                "input_suggested_interface_plan": interface_plan,
                "input_evidence_checklist_template": evidence_template,
                "input_process_code": last_result.get("process_code"),
                "llm_prompt": prompt,
                "llm_answer": answer,
                "change_request": final_change_request,
            },
        )
        return final_change_request

    @staticmethod
    def _extract_change_request(answer: str, audit: Dict[str, Any]) -> str:
        fallback = f"根据失败项 {audit.get('failed_checks') or []} 调整流程并补强工具脚本与审计策略"
        text = str(answer or "").strip()
        if not text:
            return fallback

        def pick_from_obj(obj: Any) -> str:
            if isinstance(obj, dict):
                for key in [
                    "process_change_request",
                    "change_request",
                    "suggested_change_request",
                    "request",
                    "summary",
                ]:
                    value = str(obj.get(key) or "").strip()
                    if value:
                        return value

                target = str(obj.get("prioritized_repair_target") or "").strip()
                actions = obj.get("repair_actions")
                if isinstance(actions, list):
                    action_text = "；".join(str(item).strip() for item in actions if str(item).strip())
                    if action_text:
                        if target:
                            return f"优先修复{target}：{action_text}"
                        return action_text

                evidence = obj.get("evidence_checklist")
                if isinstance(evidence, dict) and evidence:
                    return "补齐证据清单并输出明确结论段，优先覆盖失败审计项"
            if isinstance(obj, list):
                for item in obj:
                    value = str(item).strip()
                    if value:
                        return value
            return ""

        def try_json_parse(raw: str) -> str:
            try:
                parsed = json.loads(raw)
                return pick_from_obj(parsed)
            except Exception:
                return ""

        parsed_value = try_json_parse(text)
        if not parsed_value:
            fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
            if fence:
                parsed_value = try_json_parse(fence.group(1).strip())

        if parsed_value:
            return parsed_value.replace("\n", " ").strip()[:400]

        cleaned_lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("```"):
                continue
            cleaned_lines.append(line)

        if cleaned_lines:
            return " ".join(cleaned_lines)[:400]
        return fallback

    def recommend_trusted_sources(self, trusted_sources_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            "你是数据治理工艺顾问。请基于当前可信地址核实数据源配置，推荐可补充的数据源。"
            "输出JSON对象，字段: recommendations(数组)，每项包含source_name, provider, reason, trust_level, suggested_base_url。\n"
            f"当前配置: {json.dumps(trusted_sources_config, ensure_ascii=False)}\n"
            f"上下文: {json.dumps(context, ensure_ascii=False)}"
        )
        result = run_requirement_query(requirement=prompt, config=self.config)
        answer = str(result.get("answer") or "")
        payload: Dict[str, Any] = {
            "recommendations": [],
            "raw_answer": answer,
        }
        try:
            parsed = json.loads(answer)
            if isinstance(parsed, dict):
                payload = parsed
                if "raw_answer" not in payload:
                    payload["raw_answer"] = answer
            elif isinstance(parsed, list):
                payload = {
                    "recommendations": parsed,
                    "raw_answer": answer,
                }
        except Exception:
            pass
        self._append_trace(
            "recommend_trusted_sources",
            {
                "llm_prompt": prompt,
                "llm_answer": answer,
                "recommendation_count": len(list(payload.get("recommendations") or [])),
            },
        )
        return payload
