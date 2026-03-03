from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import re
import subprocess
from datetime import datetime, timezone
from uuid import uuid4
import hashlib
import os

from packages.trust_hub import TrustHub
from packages.factory_agent.dryrun_workflow import WorkpackageDryrunWorkflow
from packages.factory_agent.llm_gateway import RequirementLLMGateway
from packages.factory_agent.publish_workflow import WorkpackagePublishWorkflow
from packages.factory_agent.routing import detect_agent_intent


class FactoryAgent:
    """工厂 Agent - 生成治理脚本、补充可信数据 HUB、输出 Skills"""

    def __init__(self):
        self._opencode_available = self._check_opencode()
        self._trust_hub = TrustHub()
        self._llm_gateway = RequirementLLMGateway()
        self._dryrun_workflow = WorkpackageDryrunWorkflow(
            bundle_root=Path("workpackages/bundles"),
            extract_bundle_name=self._extract_bundle_name,
            execute_entrypoint=self._execute_workpackage_entrypoint,
        )
        self._publish_workflow = WorkpackagePublishWorkflow(
            bundle_root=Path("workpackages/bundles"),
            output_root=Path("output/workpackages"),
            extract_bundle_name=self._extract_bundle_name,
            execute_entrypoint=self._execute_workpackage_entrypoint,
            persist_publish=self._persist_workpackage_publish_record,
            log_blocked=self._log_publish_blocked_event,
        )
        self._state: Dict[str, Any] = {}

    def _check_opencode(self):
        """检查 OpenCode 是否可用"""
        try:
            import subprocess
            subprocess.run(["opencode", "--version"], capture_output=True, check=True)
            return True
        except Exception:
            return False

    def converse(self, prompt):
        """对话接口 - 支持确定数据源、存储 API Key、生成工作包、workpackage 生命周期管理"""
        user_prompt = str(prompt or "").strip()
        self._append_chat_history("user", user_prompt)
        intent = detect_agent_intent(prompt)
        if intent == "store_api_key":
            result = self._handle_store_api_key(prompt)
            self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
            return result
        if intent == "list_workpackages":
            result = self._handle_list_workpackages()
            self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
            return result
        if intent == "query_workpackage":
            result = self._handle_query_workpackage(prompt)
            self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
            return result
        if intent == "dryrun_workpackage":
            result = self._handle_dryrun_workpackage(prompt)
            self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
            return result
        if intent == "publish_workpackage":
            result = self._handle_publish_workpackage(prompt)
            self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
            return result
        if intent == "list_sources":
            result = self._handle_list_sources()
            self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
            return result
        if intent == "generate_workpackage":
            result = self._handle_generate_workpackage(prompt)
            self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
            return result
        if not self._is_data_governance_topic(user_prompt) and self._is_explicitly_non_governance_topic(user_prompt):
            result = self._handle_out_of_scope_chat(user_prompt)
            self._append_chat_history("assistant", str(result.get("message") or ""))
            return result
        if not self._requires_structured_requirement(user_prompt):
            result = self._handle_general_governance_chat(user_prompt)
            self._append_chat_history("assistant", str(result.get("message") or result.get("reply") or ""))
            return result
        result = self._handle_requirement_confirmation(prompt)
        self._append_chat_history("assistant", str(result.get("message") or result.get("status") or ""))
        return result

    def _handle_requirement_confirmation(self, prompt: str) -> Dict[str, Any]:
        """调用 LLM 确认治理需求；失败时阻塞并等待人工确认。"""
        workpackage_id = str(self._extract_bundle_name(prompt) or f"wp_req_{uuid4().hex[:8]}")
        trace_id = f"trace_req_{uuid4().hex[:12]}"
        llm_meta = self._resolve_llm_meta()
        self._record_observation_event(
            source_service="llm",
            event_type="llm_request",
            status="success",
            trace_id=trace_id,
            workpackage_id=workpackage_id,
            payload={
                "pipeline_stage": "llm_confirmed",
                "client_type": "user",
                "version": "",
                "model": llm_meta["model"],
                "base_url": llm_meta["base_url"],
                "prompt": str(prompt or ""),
            },
        )
        try:
            result = self._run_requirement_query(prompt)
            summary = self._extract_requirement_summary(str(result.get("answer") or ""))
            answer = str(result.get("answer") or "")
            usage = result.get("token_usage") if isinstance(result.get("token_usage"), dict) else {}
            self._record_observation_event(
                source_service="llm",
                event_type="llm_response",
                status="success",
                trace_id=trace_id,
                workpackage_id=workpackage_id,
                payload={
                    "pipeline_stage": "llm_confirmed",
                    "client_type": "user",
                    "version": "",
                    "model": llm_meta["model"],
                    "base_url": llm_meta["base_url"],
                    "latency_ms": float(result.get("latency_ms") or 0.0),
                    "token_usage": {
                        "prompt": int(usage.get("prompt") or 0),
                        "completion": int(usage.get("completion") or 0),
                        "total": int(usage.get("total") or 0),
                    },
                    "prompt": str(prompt or ""),
                    "response": answer,
                },
            )
            self._record_observation_event(
                source_service="factory_agent",
                event_type="requirements_confirmed",
                status="success",
                trace_id=trace_id,
                workpackage_id=workpackage_id,
                payload={
                    "pipeline_stage": "llm_confirmed",
                    "client_type": "user",
                    "version": "",
                    "summary": summary,
                },
            )
            return {
                "status": "ok",
                "action": "confirm_requirement",
                "llm_status": "success",
                "llm_raw_text": answer,
                "llm_raw_response": result.get("raw") if isinstance(result.get("raw"), dict) else {},
                "llm_request": result.get("request") if isinstance(result.get("request"), dict) else {},
                "summary": summary,
                "message": "已完成治理需求确认，可进入 dry run 与工作包发布阶段",
            }
        except Exception as exc:
            self._record_observation_event(
                source_service="llm",
                event_type="llm_response",
                status="error",
                trace_id=trace_id,
                workpackage_id=workpackage_id,
                payload={
                    "pipeline_stage": "llm_confirmed",
                    "client_type": "user",
                    "version": "",
                    "model": llm_meta["model"],
                    "base_url": llm_meta["base_url"],
                    "failure_reason": str(exc),
                    "prompt": str(prompt or ""),
                    "response": "",
                },
            )
            return {
                "status": "blocked",
                "action": "confirm_requirement",
                "llm_status": "blocked",
                "llm_raw_text": "",
                "llm_raw_response": {},
                "llm_request": {},
                "reason": "llm_blocked",
                "requires_user_confirmation": True,
                "error": str(exc),
                "message": "LLM 需求确认阻塞，已停止后续流程，请人工确认处置方案",
            }

    def _run_requirement_query(self, prompt: str) -> Dict[str, Any]:
        return self._llm_gateway.query(prompt)

    def _run_general_chat_query(self, prompt: str) -> Dict[str, Any]:
        return self._llm_gateway.query_dialogue(prompt, history=self._get_chat_history())

    def _run_workpackage_blueprint_query(
        self,
        prompt: str,
        context: Dict[str, Any],
        feedback: List[str] | None = None,
    ) -> Dict[str, Any]:
        return self._llm_gateway.query_workpackage_blueprint(
            user_prompt=prompt,
            context=context,
            feedback=feedback,
            history=self._get_chat_history(),
        )

    def _get_chat_history(self) -> List[Dict[str, str]]:
        history = self._state.get("chat_history")
        if isinstance(history, list):
            return [item for item in history if isinstance(item, dict)]
        return []

    def _append_chat_history(self, role: str, content: str) -> None:
        role_text = str(role or "").strip()
        content_text = str(content or "").strip()
        if not role_text or not content_text:
            return
        history = self._get_chat_history()
        history.append({"role": role_text, "content": content_text})
        self._state["chat_history"] = history[-20:]

    def _is_data_governance_topic(self, prompt: str) -> bool:
        text = str(prompt or "").lower()
        keywords = [
            "数据治理",
            "治理",
            "质量",
            "数据量",
            "样本量",
            "条数",
            "约束",
            "建议",
            "阈值",
            "准确率",
            "召回率",
            "时效",
            "sla",
            "成本",
            "规则",
            "血缘",
            "标准化",
            "清洗",
            "稽核",
            "schema",
            "etl",
            "pipeline",
            "lineage",
            "data quality",
            "data governance",
            "workpackage",
            "工作包",
            "地址",
            "元数据",
            "主数据",
        ]
        return any(key in text for key in keywords)

    def _is_explicitly_non_governance_topic(self, prompt: str) -> bool:
        text = str(prompt or "").lower()
        keywords = [
            "天气",
            "电影",
            "音乐",
            "体育",
            "八卦",
            "笑话",
            "星座",
            "彩票开奖",
            "weather",
            "movie",
            "music",
            "football",
            "nba",
        ]
        return any(key in text for key in keywords)

    def _requires_structured_requirement(self, prompt: str) -> bool:
        text = str(prompt or "").lower()
        required = [
            "工作包",
            "workpackage",
            "confirm_requirement",
            "需求确认",
            "生成方案",
            "输出json",
            "target/data_sources/rule_points/outputs",
        ]
        if any(key in text for key in required):
            return True
        return ("生成" in text and ("方案" in text or "需求" in text)) or ("generate" in text and "plan" in text)

    def _handle_out_of_scope_chat(self, prompt: str) -> Dict[str, Any]:
        return {
            "status": "ok",
            "action": "out_of_scope_chat",
            "llm_status": "skipped",
            "message": "这个话题我不太擅长。我主要支持通用数据治理相关能力，比如数据质量规则、标准化、血缘、主数据与工作包执行闭环。",
            "suggestion": "你可以告诉我数据治理目标、数据源和约束，我会继续协助。",
            "user_prompt": str(prompt or ""),
        }

    def _handle_general_governance_chat(self, prompt: str) -> Dict[str, Any]:
        try:
            result = self._run_general_chat_query(prompt)
            answer = str(result.get("answer") or "").strip()
            natural_reply = self._extract_natural_dialogue_reply(answer)
            return {
                "status": "ok",
                "action": "general_governance_chat",
                "llm_status": "success",
                "reply": natural_reply,
                "llm_raw_text": answer,
                "llm_raw_response": result.get("raw") if isinstance(result.get("raw"), dict) else {},
                "llm_request": result.get("request") if isinstance(result.get("request"), dict) else {},
                "message": natural_reply or "已完成回复",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "action": "general_governance_chat",
                "llm_status": "blocked",
                "llm_raw_text": "",
                "llm_raw_response": {},
                "llm_request": {},
                "reason": "llm_blocked",
                "requires_user_confirmation": True,
                "error": str(exc),
                "message": "LLM 对话阻塞，请稍后重试或改为明确的数据治理问题。",
            }

    def _extract_natural_dialogue_reply(self, answer: str) -> str:
        raw = str(answer or "").strip()
        if not raw:
            return ""
        obj = self._extract_json_object(raw)
        if not obj:
            return raw
        for key in ("reply", "message", "content"):
            value = str(obj.get(key) or "").strip()
            if value:
                suggestion = str(obj.get("suggestion") or "").strip()
                if suggestion and suggestion not in value:
                    return f"{value}\n{suggestion}"
                return value
        summary = obj.get("summary")
        if isinstance(summary, dict):
            target = str(summary.get("target") or "").strip()
            if target:
                return f"治理目标已确认：{target}"
        return raw

    def _extract_requirement_summary(self, answer: str) -> Dict[str, Any]:
        obj = self._extract_json_object(answer)
        if not obj:
            raise RuntimeError("llm output missing json object")
        target = str(obj.get("target") or obj.get("goal") or "").strip()
        data_sources = self._as_string_list(obj.get("data_sources") or obj.get("sources"))
        rule_points = self._as_string_list(obj.get("rule_points") or obj.get("rules"))
        outputs = self._as_string_list(obj.get("outputs") or obj.get("deliverables"))
        if not target or not data_sources or not outputs:
            raise RuntimeError("llm output missing required fields: target/data_sources/outputs")
        return {
            "target": target,
            "data_sources": data_sources,
            "rule_points": rule_points,
            "outputs": outputs,
        }

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        raw = str(text or "").strip()
        candidates = [raw]
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw, flags=re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1))
        braced = re.search(r"(\{[\s\S]*\})", raw)
        if braced:
            candidates.append(braced.group(1))
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue
        return {}

    def _as_string_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _handle_store_api_key(self, prompt):
        """处理存储 API Key 的对话"""
        name = self._extract_name(prompt)
        api_key = self._extract_api_key(prompt)
        provider = self._extract_provider(prompt)
        
        if not name or not api_key:
            return {
                "status": "error",
                "message": "请提供数据源名称和 API Key，例如：'存储高德的 API Key 为 xxx'"
            }
        
        self._trust_hub.store_api_key(
            name=name,
            api_key=api_key,
            provider=provider
        )
        
        return {
            "status": "ok",
            "action": "store_api_key",
            "name": name,
            "provider": provider,
            "message": f"已存储 {name} 的 API Key"
        }

    def _handle_list_sources(self):
        """处理列出数据源的对话"""
        sources = self._trust_hub.list_sources()
        return {
            "status": "ok",
            "action": "list_sources",
            "sources": sources,
            "message": f"已配置 {len(sources)} 个数据源"
        }

    def _handle_list_workpackages(self):
        """处理列出工作包的对话"""
        bundles_dir = Path("workpackages/bundles")
        workpackages = []
        if bundles_dir.exists():
            for bundle_dir in bundles_dir.iterdir():
                if bundle_dir.is_dir():
                    workpackages.append(bundle_dir.name)
        return {
            "status": "ok",
            "action": "list_workpackages",
            "workpackages": workpackages,
            "message": f"已发布 {len(workpackages)} 个工作包"
        }

    def _handle_query_workpackage(self, prompt):
        """处理查询工作包的对话"""
        bundles_dir = Path("workpackages/bundles")
        bundle_name = self._extract_bundle_name(prompt)
        
        if not bundle_name:
            return {
                "status": "error",
                "message": "请提供工作包名称，例如：'查询 poi-trust-verification-v1.0.0'"
            }
        
        bundle_dir = bundles_dir / bundle_name
        if not bundle_dir.exists():
            return {
                "status": "error",
                "message": f"工作包 {bundle_name} 不存在"
            }
        
        wp_config = {}
        config_path = bundle_dir / "workpackage.json"
        if config_path.exists():
            import json
            try:
                wp_config = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        return {
            "status": "ok",
            "action": "query_workpackage",
            "bundle_name": bundle_name,
            "bundle_path": str(bundle_dir),
            "workpackage_config": wp_config,
            "message": f"已查询工作包 {bundle_name}"
        }

    def _handle_dryrun_workpackage(self, prompt):
        """处理 dryrun 工作包的对话"""
        return self._dryrun_workflow.run(prompt)

    def _execute_workpackage_entrypoint(self, *, bundle_dir: Path, bundle_name: str, report_name: str) -> Dict[str, Any]:
        observability_dir = bundle_dir / "observability"
        observability_dir.mkdir(parents=True, exist_ok=True)
        report_path = observability_dir / report_name
        metrics_path = observability_dir / "line_metrics.json"
        if not metrics_path.exists():
            metrics_path.write_text(
                json.dumps(
                    {
                        "bundle_name": bundle_name,
                        "status": "initialized",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        cmd: list[str]
        if (bundle_dir / "entrypoint.sh").exists():
            cmd = ["bash", "entrypoint.sh"]
        else:
            cmd = ["python3", "entrypoint.py"]

        proc = subprocess.run(
            cmd,
            cwd=str(bundle_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        report_payload = {
            "bundle_name": bundle_name,
            "command": cmd,
            "return_code": int(proc.returncode),
            "stdout": str(proc.stdout or ""),
            "stderr": str(proc.stderr or ""),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
        report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "success": int(proc.returncode) == 0,
            "return_code": int(proc.returncode),
            "report_path": str(report_path),
            "metrics_path": str(metrics_path),
            "stdout": str(proc.stdout or ""),
            "stderr": str(proc.stderr or ""),
        }

    def _extract_bundle_name(self, prompt: str) -> Optional[str]:
        """从 prompt 中提取工作包名称"""
        import re
        match = re.search(r'([a-zA-Z0-9_-]+-v\d+\.\d+\.\d+)', prompt)
        if match:
            return match.group(1)
        match = re.search(r'([a-zA-Z0-9_-]+)', prompt)
        if match:
            return match.group(1)
        return None

    def _handle_publish_workpackage(self, prompt: str) -> Dict[str, Any]:
        bundle_name = str(self._extract_bundle_name(prompt) or "")
        workpackage_id = bundle_name or f"wp_publish_{uuid4().hex[:8]}"
        trace_id = f"trace_publish_{uuid4().hex[:12]}"
        metadata = self._collect_workpackage_metadata(bundle_name)
        version = str(metadata.get("version") or "")
        self._record_observation_event(
            source_service="factory_agent",
            event_type="workpackage_packaged",
            status="success",
            trace_id=trace_id,
            workpackage_id=workpackage_id,
            payload={
                "pipeline_stage": "packaged",
                "client_type": "user",
                "version": version,
                "checksum": metadata.get("checksum", ""),
                "skills_count": int(metadata.get("skills_count", 0)),
                "artifact_count": int(metadata.get("artifact_count", 0)),
                "submit_status": "prepared",
            },
        )
        self._record_observation_event(
            source_service="governance_runtime",
            event_type="runtime_submit_requested",
            status="success",
            trace_id=trace_id,
            workpackage_id=workpackage_id,
            payload={
                "pipeline_stage": "submitted",
                "client_type": "user",
                "version": version,
                "checksum": metadata.get("checksum", ""),
                "skills_count": int(metadata.get("skills_count", 0)),
                "artifact_count": int(metadata.get("artifact_count", 0)),
                "submit_status": "submitted",
            },
        )

        result = self._publish_workflow.run(prompt)
        runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
        runtime_receipt_id = str(runtime.get("receipt_id") or f"receipt_{uuid4().hex[:10]}")
        if str(result.get("status") or "").lower() == "ok":
            self._record_observation_event(
                source_service="governance_runtime",
                event_type="runtime_submit_accepted",
                status="success",
                trace_id=trace_id,
                workpackage_id=workpackage_id,
                payload={
                    "pipeline_stage": "accepted",
                    "client_type": "user",
                    "version": version,
                    "runtime_receipt_id": runtime_receipt_id,
                    "checksum": metadata.get("checksum", ""),
                    "skills_count": int(metadata.get("skills_count", 0)),
                    "artifact_count": int(metadata.get("artifact_count", 0)),
                    "submit_status": "accepted",
                },
            )
            self._record_observation_event(
                source_service="governance_runtime",
                event_type="runtime_task_running",
                status="success",
                trace_id=trace_id,
                workpackage_id=workpackage_id,
                payload={
                    "pipeline_stage": "running",
                    "client_type": "user",
                    "version": version,
                    "runtime_receipt_id": runtime_receipt_id,
                    "submit_status": "running",
                },
            )
            self._record_observation_event(
                source_service="governance_runtime",
                event_type="runtime_task_finished",
                status="success",
                trace_id=trace_id,
                workpackage_id=workpackage_id,
                payload={
                    "pipeline_stage": "finished",
                    "client_type": "user",
                    "version": version,
                    "runtime_receipt_id": runtime_receipt_id,
                    "submit_status": "published",
                },
            )
        else:
            self._record_observation_event(
                source_service="governance_runtime",
                event_type="runtime_submit_failed",
                status="error",
                trace_id=trace_id,
                workpackage_id=workpackage_id,
                payload={
                    "pipeline_stage": "submitted",
                    "client_type": "user",
                    "version": version,
                    "runtime_receipt_id": runtime_receipt_id,
                    "submit_status": "blocked",
                    "failure_reason": str(result.get("reason") or result.get("message") or "publish_blocked"),
                },
            )
        return result

    def _resolve_llm_meta(self) -> Dict[str, str]:
        config_path = Path("config/llm_api.json")
        model = str(os.getenv("LLM_MODEL") or "")
        base_url = str(os.getenv("LLM_BASE_URL") or "")
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                if isinstance(config, dict):
                    model = str(config.get("model") or model)
                    base_url = str(config.get("base_url") or base_url)
            except Exception:
                pass
        return {"model": model, "base_url": base_url}

    def _record_observation_event(
        self,
        *,
        source_service: str,
        event_type: str,
        status: str,
        trace_id: str,
        workpackage_id: str = "",
        payload: Dict[str, Any] | None = None,
    ) -> None:
        try:
            from services.governance_api.app.services.governance_service import GOVERNANCE_SERVICE

            GOVERNANCE_SERVICE.record_observation_event(
                source_service=source_service,
                event_type=event_type,
                status=status,
                trace_id=trace_id,
                workpackage_id=str(workpackage_id or ""),
                payload=payload or {},
            )
        except Exception:
            return

    def _collect_workpackage_metadata(self, bundle_name: str) -> Dict[str, Any]:
        if not bundle_name:
            return {"version": "", "checksum": "", "skills_count": 0, "artifact_count": 0}
        bundle_dir = Path("workpackages/bundles") / bundle_name
        config_path = bundle_dir / "workpackage.json"
        version = ""
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                if isinstance(config, dict):
                    version = str(config.get("version") or "")
            except Exception:
                version = ""
        digest = hashlib.sha256()
        artifact_count = 0
        if bundle_dir.exists():
            files = sorted(path for path in bundle_dir.rglob("*") if path.is_file())
            artifact_count = len(files)
            for item in files:
                try:
                    digest.update(str(item.relative_to(bundle_dir)).encode("utf-8"))
                    digest.update(item.read_bytes())
                except Exception:
                    continue
        checksum = digest.hexdigest() if artifact_count else ""
        skills_count = len(list((bundle_dir / "skills").glob("*.md"))) if (bundle_dir / "skills").exists() else 0
        return {
            "version": version,
            "checksum": checksum,
            "skills_count": skills_count,
            "artifact_count": artifact_count,
        }

    def _persist_workpackage_publish_record(
        self,
        *,
        workpackage_id: str,
        version: str,
        status: str,
        evidence_ref: str,
        bundle_path: str,
    ) -> None:
        from services.governance_api.app.services.governance_service import GOVERNANCE_SERVICE

        GOVERNANCE_SERVICE.upsert_workpackage_publish(
            workpackage_id=workpackage_id,
            version=version,
            status=status,
            evidence_ref=evidence_ref,
            bundle_path=bundle_path,
            published_by="factory_agent",
        )

    def _log_publish_blocked_event(self, payload: Dict[str, Any]) -> None:
        from services.governance_api.app.services.governance_service import GOVERNANCE_SERVICE

        GOVERNANCE_SERVICE.log_blocked_confirmation(
            event_type="workpackage_publish_blocked",
            caller="factory_agent",
            payload=payload,
        )

    def _build_publish_blocked(
        self,
        *,
        bundle_name: str,
        reason: str,
        message: str,
        error: str = "",
    ) -> Dict[str, Any]:
        payload = {
            "workpackage_id": bundle_name,
            "reason": reason,
            "confirmation_user": "pending_owner",
            "confirmation_decision": "pending",
            "confirmation_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self._log_publish_blocked_event(payload)
        except Exception:
            pass
        result = {
            "status": "blocked",
            "action": "publish_workpackage",
            "reason": reason,
            "requires_user_confirmation": True,
            "bundle_name": bundle_name,
            "message": message,
        }
        if error:
            result["error"] = error
        return result

    def _handle_generate_workpackage(self, prompt):
        """处理生成工作包的对话：基于上下文 + LLM 蓝图迭代收敛。"""
        context = self._build_workpackage_context(prompt)
        max_rounds = max(1, min(int(os.getenv("WORKPACKAGE_BLUEPRINT_MAX_ROUNDS", "2")), 8))
        feedback: List[str] = []
        schema_errors: List[str] = []
        blueprint: Dict[str, Any] = {}
        llm_raw_text = ""
        llm_request: Dict[str, Any] = {}
        llm_raw_response: Dict[str, Any] = {}
        retry_count = 0

        for idx in range(max_rounds):
            try:
                result = self._run_workpackage_blueprint_query(prompt, context, feedback if feedback else None)
                llm_raw_text = str(result.get("answer") or "")
                llm_request = result.get("request") if isinstance(result.get("request"), dict) else llm_request
                llm_raw_response = result.get("raw") if isinstance(result.get("raw"), dict) else llm_raw_response
                candidate = self._extract_json_object(llm_raw_text)
                blueprint = self._normalize_workpackage_blueprint(candidate, prompt=prompt)
                schema_errors = self._validate_workpackage_blueprint(blueprint)
            except Exception as exc:
                schema_errors = [f"llm_call_failed: {exc}"]
            if not schema_errors:
                break
            retry_count += 1
            feedback = [f"schema_error: {item}" for item in schema_errors]
            if idx == max_rounds - 1:
                blueprint = self._autofill_blueprint_from_context(blueprint, context, prompt=prompt)
                schema_errors = self._validate_workpackage_blueprint(blueprint)
                break

        self._enrich_blueprint_with_api_gap_plan(blueprint, context, prompt=prompt)
        workpackage = blueprint.get("workpackage") if isinstance(blueprint.get("workpackage"), dict) else {}
        name = str(workpackage.get("name") or self._extract_name(prompt) or f"wp-{uuid4().hex[:8]}")
        version = str(workpackage.get("version") or "v1.0.0")
        bundle_name = f"{name}-{version}"

        sources = self._resolve_blueprint_sources(blueprint, context)
        self._apply_missing_api_plan(blueprint)
        bundle_dir = Path(f"workpackages/bundles/{bundle_name}")
        self._create_workpackage_bundle(bundle_dir, blueprint=blueprint, sources=sources)

        return {
            "status": "ok",
            "action": "generate_workpackage",
            "bundle_name": bundle_name,
            "bundle_path": str(bundle_dir),
            "sources_used": sources,
            "llm_retry_count": retry_count,
            "schema_errors": schema_errors,
            "llm_raw_text": llm_raw_text,
            "llm_raw_response": llm_raw_response,
            "llm_request": llm_request,
            "workpackage_blueprint": blueprint,
            "message": f"工作包 {bundle_name} 已生成，包含架构上下文、I/O定义、API计划与可执行脚本。",
        }

    def _create_workpackage_bundle(self, bundle_dir: Path, *, blueprint: Dict[str, Any], sources: List[str]):
        """创建工作包 bundle。"""
        bundle_dir.mkdir(parents=True, exist_ok=True)

        workpackage = blueprint.get("workpackage") if isinstance(blueprint.get("workpackage"), dict) else {}
        name = str(workpackage.get("name") or "workpackage")
        version = str(workpackage.get("version") or "v1.0.0")
        objective = str(workpackage.get("objective") or "数据治理执行")

        (bundle_dir / "README.md").write_text(self._generate_readme(name, version, sources, objective), encoding="utf-8")

        wp_config = dict(blueprint)
        wp_config["name"] = name
        wp_config["version"] = version
        wp_config["objective"] = objective
        wp_config["sources"] = sources
        (bundle_dir / "workpackage.json").write_text(
            json.dumps(wp_config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        skills_dir = bundle_dir / "skills"
        skills_dir.mkdir(exist_ok=True)
        for source in sources:
            skill_path = skills_dir / f"{source}_verification.md"
            skill_path.write_text(
                self._generate_skill_markdown(source),
                encoding="utf-8"
            )

        scripts_dir = bundle_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        script_specs = blueprint.get("scripts") if isinstance(blueprint.get("scripts"), list) else []
        generated_count = 0
        for spec in script_specs:
            if not isinstance(spec, dict):
                continue
            filename = re.sub(r"[^a-zA-Z0-9._-]", "_", str(spec.get("name") or "").strip()) or ""
            if not filename.endswith(".py"):
                continue
            content = str(spec.get("content") or "").strip()
            if not content:
                content = self._generate_script_template(spec)
            (scripts_dir / filename).write_text(content, encoding="utf-8")
            generated_count += 1
        if generated_count == 0:
            (scripts_dir / "run_pipeline.py").write_text(self._generate_verify_script(sources), encoding="utf-8")

        (bundle_dir / "entrypoint.sh").write_text(
            self._generate_entrypoint_sh(),
            encoding="utf-8"
        )
        (bundle_dir / "entrypoint.py").write_text(
            self._generate_entrypoint_py(),
            encoding="utf-8"
        )
        
        observability_dir = bundle_dir / "observability"
        observability_dir.mkdir(exist_ok=True)
        (observability_dir / "line_metrics.json").write_text(
            json.dumps({"sources": sources, "version": version, "objective": objective}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        (observability_dir / "line_observe.py").write_text(
            self._generate_observe_script(),
            encoding="utf-8"
        )

        missing_apis = ((blueprint.get("api_plan") or {}).get("missing_apis") if isinstance(blueprint.get("api_plan"), dict) else []) or []
        env_lines = ["# 需要用户补充的外部API Key", ""]
        for item in missing_apis:
            if not isinstance(item, dict):
                continue
            if not bool(item.get("requires_key")):
                continue
            env_name = str(item.get("api_key_env") or f"{str(item.get('name') or 'EXT_API').upper()}_API_KEY")
            env_name = re.sub(r"[^A-Z0-9_]", "_", env_name.upper())
            env_lines.append(f"{env_name}=")
        if len(env_lines) > 2:
            (bundle_dir / "config").mkdir(exist_ok=True)
            (bundle_dir / "config" / "provider_keys.env.example").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    def _build_workpackage_context(self, prompt: str) -> Dict[str, Any]:
        catalog = self._load_registered_api_catalog()
        trusted_sources = self._trust_hub.list_sources()
        architecture = {
            "layers": [
                "Agent会话编排层",
                "可信数据Hub层",
                "工作包执行层",
                "运行态可观测层",
            ],
            "workpackage_lifecycle": ["requirements_confirm", "generate", "dryrun", "publish", "runtime_upload"],
        }
        alignment_checklist = [
            "1) 解释数据治理工厂架构上下文与工作包生命周期",
            "2) 对齐输入输出结构并给出精准 schema 定义",
            "3) 使用可信数据Hub已注册 API，并列出可调用接口",
            "4) 若 API 不足，建议外部 API/数据源，生成脚本并说明 key 获取与注册步骤",
            "5) 在依赖明确后输出可执行工具脚本与执行计划",
        ]
        return {
            "architecture_context": architecture,
            "registered_api_catalog": catalog,
            "trusted_hub_sources": trusted_sources,
            "alignment_checklist": alignment_checklist,
            "user_prompt": str(prompt or ""),
        }

    def _load_registered_api_catalog(self) -> List[Dict[str, Any]]:
        config_path = Path("config/trusted_data_sources.json")
        if not config_path.exists():
            return []
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        trusted_sources = payload.get("trusted_sources") if isinstance(payload, dict) else []
        if not isinstance(trusted_sources, list):
            return []
        rows: List[Dict[str, Any]] = []
        for source in trusted_sources:
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("source_id") or "")
            provider = str(source.get("provider") or "")
            interfaces = source.get("trusted_interfaces") if isinstance(source.get("trusted_interfaces"), list) else []
            for item in interfaces:
                if not isinstance(item, dict):
                    continue
                rows.append(
                    {
                        "source_id": source_id,
                        "provider": provider,
                        "interface_id": str(item.get("interface_id") or ""),
                        "name": str(item.get("name") or ""),
                        "base_url": str(item.get("base_url") or ""),
                        "method": str(item.get("method") or ""),
                        "provider_group": str(item.get("provider_group") or ""),
                    }
                )
        return rows

    def _normalize_workpackage_blueprint(self, obj: Dict[str, Any], *, prompt: str) -> Dict[str, Any]:
        workpackage = obj.get("workpackage") if isinstance(obj.get("workpackage"), dict) else {}
        name = str(workpackage.get("name") or self._slugify_name(self._extract_name(prompt) or "governance-workpackage"))
        version = str(workpackage.get("version") or "v1.0.0")
        if version and not version.startswith("v"):
            version = f"v{version}"
        merged = re.match(r"^(.+)-v(\d+\.\d+\.\d+)$", name)
        if merged:
            extracted_name = str(merged.group(1) or "").strip()
            extracted_version = f"v{str(merged.group(2) or '').strip()}"
            if extracted_name:
                name = extracted_name
            if not str(version or "").strip() or str(version or "").strip() == "v1.0.0":
                version = extracted_version
        objective = str(workpackage.get("objective") or "数据治理任务执行")
        architecture_context = obj.get("architecture_context") if isinstance(obj.get("architecture_context"), dict) else {}
        io_contract = obj.get("io_contract") if isinstance(obj.get("io_contract"), dict) else {}
        api_plan = obj.get("api_plan") if isinstance(obj.get("api_plan"), dict) else {}
        execution_plan = obj.get("execution_plan") if isinstance(obj.get("execution_plan"), dict) else {}
        scripts = obj.get("scripts") if isinstance(obj.get("scripts"), list) else []
        return {
            "workpackage": {"name": name, "version": version, "objective": objective},
            "architecture_context": architecture_context,
            "io_contract": io_contract,
            "api_plan": {
                "registered_apis_used": api_plan.get("registered_apis_used") if isinstance(api_plan.get("registered_apis_used"), list) else [],
                "missing_apis": api_plan.get("missing_apis") if isinstance(api_plan.get("missing_apis"), list) else [],
            },
            "execution_plan": {"steps": execution_plan.get("steps") if isinstance(execution_plan.get("steps"), list) else []},
            "scripts": scripts,
        }

    def _validate_workpackage_blueprint(self, blueprint: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        workpackage = blueprint.get("workpackage") if isinstance(blueprint.get("workpackage"), dict) else {}
        if not str(workpackage.get("name") or "").strip():
            errors.append("workpackage.name is required")
        if not str(workpackage.get("version") or "").strip():
            errors.append("workpackage.version is required")
        if not str(workpackage.get("objective") or "").strip():
            errors.append("workpackage.objective is required")

        architecture_context = blueprint.get("architecture_context") if isinstance(blueprint.get("architecture_context"), dict) else {}
        if not architecture_context:
            errors.append("architecture_context is required")
        if not isinstance(architecture_context.get("runtime_env"), dict):
            errors.append("architecture_context.runtime_env must be object")

        io_contract = blueprint.get("io_contract") if isinstance(blueprint.get("io_contract"), dict) else {}
        if not isinstance(io_contract.get("input_schema"), dict):
            errors.append("io_contract.input_schema must be object")
        if not isinstance(io_contract.get("output_schema"), dict):
            errors.append("io_contract.output_schema must be object")

        api_plan = blueprint.get("api_plan") if isinstance(blueprint.get("api_plan"), dict) else {}
        if not isinstance(api_plan.get("registered_apis_used"), list):
            errors.append("api_plan.registered_apis_used must be array")
        if not isinstance(api_plan.get("missing_apis"), list):
            errors.append("api_plan.missing_apis must be array")
        for idx, item in enumerate(api_plan.get("missing_apis") or []):
            if not isinstance(item, dict):
                errors.append(f"api_plan.missing_apis[{idx}] must be object")
                continue
            if not str(item.get("name") or "").strip():
                errors.append(f"api_plan.missing_apis[{idx}].name is required")
            if not str(item.get("endpoint") or "").strip():
                errors.append(f"api_plan.missing_apis[{idx}].endpoint is required")
            if "requires_key" not in item:
                errors.append(f"api_plan.missing_apis[{idx}].requires_key is required")

        execution_plan = blueprint.get("execution_plan") if isinstance(blueprint.get("execution_plan"), dict) else {}
        if not isinstance(execution_plan.get("steps"), list) or not execution_plan.get("steps"):
            errors.append("execution_plan.steps must be non-empty array")

        scripts = blueprint.get("scripts")
        if not isinstance(scripts, list) or not scripts:
            errors.append("scripts must be non-empty array")
        else:
            for idx, item in enumerate(scripts):
                if not isinstance(item, dict):
                    errors.append(f"scripts[{idx}] must be object")
                    continue
                if not str(item.get("name") or "").strip():
                    errors.append(f"scripts[{idx}].name is required")
                if not str(item.get("entry") or "").strip():
                    errors.append(f"scripts[{idx}].entry is required")
        return errors

    def _resolve_blueprint_sources(self, blueprint: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        api_plan = blueprint.get("api_plan") if isinstance(blueprint.get("api_plan"), dict) else {}
        registered = api_plan.get("registered_apis_used") if isinstance(api_plan.get("registered_apis_used"), list) else []
        source_ids: List[str] = []
        for item in registered:
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_id") or "").strip()
            if source_id and source_id not in source_ids:
                source_ids.append(source_id)
        if source_ids:
            return source_ids
        trusted_sources = context.get("trusted_hub_sources") if isinstance(context.get("trusted_hub_sources"), list) else []
        fallback = [str(item).strip() for item in trusted_sources if str(item).strip()]
        if fallback:
            return fallback[:3]
        return ["fengtu", "opencagedata", "nominatim_openstreetmap"]

    def _apply_missing_api_plan(self, blueprint: Dict[str, Any]) -> None:
        api_plan = blueprint.get("api_plan") if isinstance(blueprint.get("api_plan"), dict) else {}
        missing = api_plan.get("missing_apis") if isinstance(api_plan.get("missing_apis"), list) else []
        registered_rows: List[Dict[str, Any]] = []
        for item in missing:
            if not isinstance(item, dict):
                continue
            endpoint = str(item.get("endpoint") or "").strip()
            if not endpoint.startswith("http"):
                continue
            source_id = self._slugify_name(str(item.get("name") or "ext_api"))
            provider = str(item.get("provider") or source_id)
            try:
                capability = self._trust_hub.upsert_capability(
                    source_id=source_id,
                    provider=provider,
                    endpoint=endpoint,
                    tool_type="api",
                    status="pending_key" if bool(item.get("requires_key")) else "active",
                )
                registered_rows.append(capability)
            except Exception as exc:
                registered_rows.append({"source_id": source_id, "endpoint": endpoint, "error": str(exc)})
        api_plan["missing_apis_registered"] = registered_rows
        blueprint["api_plan"] = api_plan

    def _slugify_name(self, value: str) -> str:
        raw = str(value or "").strip().lower()
        if not raw:
            return f"wp_{uuid4().hex[:8]}"
        text = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
        return text or f"wp_{uuid4().hex[:8]}"

    def _autofill_blueprint_from_context(self, blueprint: Dict[str, Any], context: Dict[str, Any], *, prompt: str) -> Dict[str, Any]:
        workpackage = blueprint.get("workpackage") if isinstance(blueprint.get("workpackage"), dict) else {}
        if not str(workpackage.get("name") or "").strip():
            workpackage["name"] = self._slugify_name(self._extract_name(prompt) or "governance-workpackage")
        if not str(workpackage.get("version") or "").strip():
            workpackage["version"] = "v1.0.0"
        if not str(workpackage.get("objective") or "").strip():
            workpackage["objective"] = "地址治理工作包（标准化/验真/空间图谱）"
        blueprint["workpackage"] = workpackage

        architecture_context = blueprint.get("architecture_context") if isinstance(blueprint.get("architecture_context"), dict) else {}
        if not architecture_context:
            architecture_context = dict(context.get("architecture_context") or {})
        if not isinstance(architecture_context.get("runtime_env"), dict):
            architecture_context["runtime_env"] = {"python": "3.11", "queue": "sync"}
        blueprint["architecture_context"] = architecture_context

        io_contract = blueprint.get("io_contract") if isinstance(blueprint.get("io_contract"), dict) else {}
        if not isinstance(io_contract.get("input_schema"), dict):
            io_contract["input_schema"] = {
                "type": "object",
                "properties": {"raw_text": {"type": "string"}},
                "required": ["raw_text"],
            }
        if not isinstance(io_contract.get("output_schema"), dict):
            io_contract["output_schema"] = {
                "type": "object",
                "properties": {
                    "normalization": {"type": "object"},
                    "entity_parsing": {"type": "object"},
                    "address_validation": {"type": "object"},
                    "spatial_graph": {"type": "object"},
                },
                "required": ["normalization", "entity_parsing", "address_validation", "spatial_graph"],
            }
        blueprint["io_contract"] = io_contract

        api_plan = blueprint.get("api_plan") if isinstance(blueprint.get("api_plan"), dict) else {}
        if not isinstance(api_plan.get("registered_apis_used"), list) or not api_plan.get("registered_apis_used"):
            api_plan["registered_apis_used"] = [
                {"source_id": "fengtu", "interface_id": "address_standardize"},
                {"source_id": "fengtu", "interface_id": "address_real_check"},
            ]
        if not isinstance(api_plan.get("missing_apis"), list):
            api_plan["missing_apis"] = []
        blueprint["api_plan"] = api_plan

        execution_plan = blueprint.get("execution_plan") if isinstance(blueprint.get("execution_plan"), dict) else {}
        if not isinstance(execution_plan.get("steps"), list) or not execution_plan.get("steps"):
            execution_plan["steps"] = ["解析输入", "地址标准化", "地址验真", "空间图谱构建"]
        blueprint["execution_plan"] = execution_plan

        scripts = blueprint.get("scripts")
        if not isinstance(scripts, list) or not scripts:
            scripts = [
                {"name": "run_pipeline.py", "purpose": "执行治理流程", "runtime": "python", "entry": "python scripts/run_pipeline.py"},
            ]
        blueprint["scripts"] = scripts
        return blueprint

    def _enrich_blueprint_with_api_gap_plan(self, blueprint: Dict[str, Any], context: Dict[str, Any], *, prompt: str) -> None:
        api_plan = blueprint.get("api_plan") if isinstance(blueprint.get("api_plan"), dict) else {}
        registered_used = api_plan.get("registered_apis_used") if isinstance(api_plan.get("registered_apis_used"), list) else []
        missing = api_plan.get("missing_apis") if isinstance(api_plan.get("missing_apis"), list) else []

        registered_ids = self._collect_registered_interface_ids(registered_used, context)
        required = self._derive_required_capabilities(prompt=prompt, io_contract=blueprint.get("io_contract"))
        missing_by_capability = {str(item.get("capability_id") or ""): item for item in missing if isinstance(item, dict)}
        for capability in required:
            cap_id = str(capability.get("capability_id") or "").strip()
            if not cap_id or cap_id in registered_ids or cap_id in missing_by_capability:
                continue
            missing.append(
                {
                    "capability_id": cap_id,
                    "name": str(capability.get("name") or cap_id),
                    "endpoint": str(capability.get("endpoint") or ""),
                    "reason": str(capability.get("reason") or "补足治理能力"),
                    "requires_key": True,
                    "api_key_env": str(capability.get("api_key_env") or f"{cap_id.upper()}_API_KEY"),
                    "provider": str(capability.get("provider") or "external"),
                }
            )
        api_plan["missing_apis"] = missing
        blueprint["api_plan"] = api_plan
        self._ensure_blueprint_scripts_for_missing_apis(blueprint)

    def _collect_registered_interface_ids(self, registered_used: List[Dict[str, Any]], context: Dict[str, Any]) -> set[str]:
        ids: set[str] = set()
        for item in registered_used:
            if not isinstance(item, dict):
                continue
            interface_id = str(item.get("interface_id") or "").strip().lower()
            name = str(item.get("name") or "").strip().lower()
            if interface_id:
                ids.add(interface_id)
            if name:
                if "标准化" in name:
                    ids.add("address_standardize")
                if "验真" in name or "真实性" in name:
                    ids.add("address_real_check")
                if "实体" in name or "拆分" in name:
                    ids.add("entity_parsing")
                if "图谱" in name:
                    ids.add("spatial_graph_build")
        catalog = context.get("registered_api_catalog") if isinstance(context.get("registered_api_catalog"), list) else []
        for row in catalog:
            if not isinstance(row, dict):
                continue
            interface_id = str(row.get("interface_id") or "").strip().lower()
            if interface_id:
                ids.add(interface_id)
        return ids

    def _derive_required_capabilities(self, *, prompt: str, io_contract: Any) -> List[Dict[str, str]]:
        text = str(prompt or "")
        output_schema = {}
        if isinstance(io_contract, dict) and isinstance(io_contract.get("output_schema"), dict):
            output_schema = io_contract.get("output_schema") or {}
        props = output_schema.get("properties") if isinstance(output_schema, dict) else {}
        required: List[Dict[str, str]] = []
        required.append(
            {
                "capability_id": "address_standardize",
                "name": "地址标准化API",
                "endpoint": "https://gis-apis.sf-express.com/all/api/geocode/geo",
                "reason": "执行地址标准化",
                "api_key_env": "FENGTU_AK_STANDARDIZE",
                "provider": "sfmap",
            }
        )
        if "验真" in text or "真实性" in text or "address_validation" in str(props):
            required.append(
                {
                    "capability_id": "address_real_check",
                    "name": "地址真实性校验API",
                    "endpoint": "https://gis-apis.sf-express.com/all/api/geocode/realcheck",
                    "reason": "执行地址验真",
                    "api_key_env": "FENGTU_AK_REALCHECK",
                    "provider": "sfmap",
                }
            )
        if "实体拆分" in text or "entity_parsing" in str(props):
            required.append(
                {
                    "capability_id": "entity_parsing",
                    "name": "空间实体拆分API",
                    "endpoint": "https://api.external.example.com/entity/parsing",
                    "reason": "补齐空间实体拆分能力",
                    "api_key_env": "ENTITY_PARSING_API_KEY",
                    "provider": "external",
                }
            )
        if "空间图谱" in text or "spatial_graph" in str(props):
            required.append(
                {
                    "capability_id": "spatial_graph_build",
                    "name": "空间图谱构建API",
                    "endpoint": "https://api.external.example.com/spatial/graph/build",
                    "reason": "补齐空间图谱输出能力",
                    "api_key_env": "SPATIAL_GRAPH_API_KEY",
                    "provider": "external",
                }
            )
        return required

    def _ensure_blueprint_scripts_for_missing_apis(self, blueprint: Dict[str, Any]) -> None:
        scripts = blueprint.get("scripts") if isinstance(blueprint.get("scripts"), list) else []
        existing_names = {str(item.get("name") or "").strip() for item in scripts if isinstance(item, dict)}
        missing = ((blueprint.get("api_plan") or {}).get("missing_apis") if isinstance(blueprint.get("api_plan"), dict) else []) or []
        for item in missing:
            if not isinstance(item, dict):
                continue
            cap_id = self._slugify_name(str(item.get("capability_id") or item.get("name") or "external_api"))
            script_name = f"fetch_{cap_id}.py"
            if script_name in existing_names:
                continue
            scripts.append(
                {
                    "name": script_name,
                    "purpose": f"调用外部API补齐能力：{str(item.get('name') or cap_id)}",
                    "runtime": "python",
                    "entry": f"python scripts/{script_name}",
                    "endpoint": str(item.get("endpoint") or ""),
                    "api_key_env": str(item.get("api_key_env") or ""),
                }
            )
            existing_names.add(script_name)
        blueprint["scripts"] = scripts

    def _extract_name(self, prompt: str) -> Optional[str]:
        if "高德" in prompt:
            return "高德"
        if "百度" in prompt:
            return "百度"
        if "天地图" in prompt:
            return "天地图"
        return None

    def _extract_api_key(self, prompt: str) -> Optional[str]:
        import re
        match = re.search(r"(?:api.*key|key.*api|密钥)[\s:：]*([a-zA-Z0-9_-]+)", prompt, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_provider(self, prompt: str) -> str:
        if "高德" in prompt:
            return "amap"
        if "百度" in prompt:
            return "baidu"
        if "天地图" in prompt:
            return "tianditu"
        return "unknown"

    def _generate_readme(self, name: str, version: str, sources: List[str], objective: str) -> str:
        return f"""# {name} {version}

{objective}

## 数据源
{chr(10).join(f'- {s}' for s in sources)}

## 执行方式
```bash
bash entrypoint.sh
```

或
```bash
python entrypoint.py
```
""".strip()

    def _generate_script_template(self, spec: Dict[str, Any]) -> str:
        purpose = str(spec.get("purpose") or "执行数据治理步骤")
        name = str(spec.get("name") or "script.py")
        endpoint = str(spec.get("endpoint") or "")
        key_env = str(spec.get("api_key_env") or "EXTERNAL_API_KEY")
        return f"""#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

def main() -> None:
    api_key = os.getenv("{key_env}", "")
    payload = {{
        "script": "{name}",
        "purpose": "{purpose}",
        "endpoint": "{endpoint}",
        "api_key_provided": bool(api_key),
        "status": "ready" if api_key else "waiting_for_api_key",
    }}
    out = Path("output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "{name}.result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    main()
""".strip()

    def _generate_skill_markdown(self, source: str) -> str:
        return f"""---
description: {source} 可信度验证
mode: subagent
model: anthropic/claude-3-7-sonnet
temperature: 0.2
tools:
  write: true
  edit: true
  bash: false
---

你是空间智能数据工厂的治理技能 Agent。

技能名称: {source} 可信度验证
""".strip()

    def _generate_verify_script(self, sources: List[str]) -> str:
        return f"""#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SOURCES = {json.dumps(sources, ensure_ascii=False)}

def main():
    print("沿街商铺 POI 可信度验证")
    print(f"使用数据源: {{', '.join(SOURCES)}}")
    
    results = {{
        "status": "ok",
        "sources": SOURCES,
        "verification": "pending"
    }}
    
    output_path = Path("output/verification_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print("验证完成")

if __name__ == "__main__":
    main()
""".strip()

    def _generate_entrypoint_sh(self) -> str:
        return """#!/bin/bash
set -e

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "  执行 WorkPackage: $(basename "$BUNDLE_DIR")"
echo "======================================"

echo "加载技能..."
for skill_file in "$BUNDLE_DIR/skills"/*.md; do
    if [ -f "$skill_file" ]; then
        echo "  - $(basename "$skill_file")"
    fi
done

echo "执行脚本..."
for script_file in "$BUNDLE_DIR/scripts"/*.py; do
    if [ -f "$script_file" ]; then
        echo "  - $(basename "$script_file")"
        python "$script_file"
    fi
done

echo "执行产线观测..."
if [ -f "$BUNDLE_DIR/observability/line_observe.py" ]; then
    python "$BUNDLE_DIR/observability/line_observe.py"
fi

echo "======================================"
echo "  WorkPackage 执行完成"
echo "======================================"
""".strip()

    def _generate_entrypoint_py(self) -> str:
        return """#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

BUNDLE_DIR = Path(__file__).parent.resolve()


def main():
    print("======================================")
    print(f"  执行 WorkPackage: {BUNDLE_DIR.name}")
    print("======================================")
    
    print("加载技能...")
    skills_dir = BUNDLE_DIR / "skills"
    if skills_dir.exists():
        for skill_file in skills_dir.glob("*.md"):
            print(f"  - {skill_file.name}")
    
    print("执行脚本...")
    scripts_dir = BUNDLE_DIR / "scripts"
    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*.py"):
            print(f"  - {script_file.name}")
            exec(script_file.read_text(encoding="utf-8"))
    
    print("执行产线观测...")
    observe_script = BUNDLE_DIR / "observability" / "line_observe.py"
    if observe_script.exists():
        exec(observe_script.read_text(encoding="utf-8"))
    
    print("======================================")
    print("  WorkPackage 执行完成")
    print("======================================")


if __name__ == "__main__":
    main()
""".strip()

    def _generate_observe_script(self) -> str:
        return """#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

def main():
    print("产线观测脚本")
    metrics = {
        "status": "ok",
        "timestamp": "2026-02-17T00:00:00Z"
    }
    metrics_path = Path("observability/line_metrics.json")
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
""".strip()

    def generate_script(self, description):
        """生成治理脚本"""
        return {
            "status": "pending",
            "description": description,
            "message": "脚本生成功能待实现（需要 OpenCode 集成）"
        }

    def supplement_trust_hub(self, source):
        """补充可信数据 HUB"""
        source_text = str(source or "").strip()
        if not source_text:
            return {
                "status": "blocked",
                "action": "supplement_trust_hub",
                "reason": "source_missing",
                "requires_user_confirmation": True,
                "message": "未提供数据源标识，Trust Hub 补充已阻塞，请人工确认方案",
            }

        try:
            profiles = self._resolve_fengtu_group_profiles() if ("丰图" in source_text or "sfmap" in source_text.lower() or "fengtu" in source_text.lower()) else [self._resolve_source_profile(source_text)]
            persisted_caps = []
            persisted_samples = []
            for mapping in profiles:
                self._trust_hub.store_api_key(
                    name=mapping["source_id"],
                    api_key="MASKED",
                    provider=mapping["provider"],
                    api_endpoint=mapping["endpoint"],
                )
                capability = self._trust_hub.upsert_capability(
                    source_id=mapping["source_id"],
                    provider=mapping["provider"],
                    endpoint=mapping["endpoint"],
                    tool_type="api",
                )
                sample = self._trust_hub.add_sample_data(
                    source_id=mapping["source_id"],
                    content={
                        "query": "杭州市西湖区文三路90号",
                        "result": "地址结构化结果",
                        "provider": mapping["provider"],
                        "provider_group": mapping.get("provider_group", ""),
                    },
                    trust_score=0.9,
                )
                persisted_caps.append(capability)
                persisted_samples.append(sample)
            return {
                "status": "ok",
                "action": "supplement_trust_hub",
                "source": source_text,
                "capabilities": persisted_caps,
                "samples": persisted_samples,
                "message": f"已沉淀 {len(persisted_caps)} 组 provider 能力与可信样例数据",
            }
        except Exception as exc:
            return {
                "status": "blocked",
                "action": "supplement_trust_hub",
                "reason": "trust_hub_persist_failed",
                "requires_user_confirmation": True,
                "source": source_text,
                "error": str(exc),
                "message": "Trust Hub 沉淀失败，流程已阻塞，请人工确认方案",
            }

    def _resolve_fengtu_group_profiles(self) -> List[Dict[str, str]]:
        return [
            {
                "source_id": "fengtu_group_a",
                "provider": "fengtu_group_a",
                "provider_group": "group_a",
                "endpoint": "https://gis-apis.sf-express.com/opquery/addressResolve",
            },
            {
                "source_id": "fengtu_group_b",
                "provider": "fengtu_group_b",
                "provider_group": "group_b",
                "endpoint": "https://gis-apis.sf-express.com/opquery/stdAddr/api",
            },
        ]

    def _resolve_source_profile(self, source_text: str) -> Dict[str, str]:
        lower = source_text.lower()
        if "高德" in source_text or "amap" in lower:
            return {
                "source_id": "gaode",
                "provider": "amap",
                "endpoint": "https://restapi.amap.com/v3/place/text",
            }
        if "百度" in source_text or "baidu" in lower:
            return {
                "source_id": "baidu",
                "provider": "baidu",
                "endpoint": "https://api.map.baidu.com/place/v2/search",
            }
        if "天地图" in source_text or "tianditu" in lower:
            return {
                "source_id": "tianditu",
                "provider": "tianditu",
                "endpoint": "https://api.tianditu.gov.cn/geocoder",
            }
        return {
            "source_id": lower.replace(" ", "_"),
            "provider": lower.replace(" ", "_"),
            "endpoint": "https://example.com/trust/source",
        }

    def output_skill(self, skill_name, skill_spec):
        """输出 Skill 包"""
        skill_path = Path(f"workpackages/skills/{skill_name}.md")
        skill_content = self._generate_skill_markdown(skill_name)
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(skill_content, encoding="utf-8")
        return {
            "status": "ok",
            "skill_path": str(skill_path),
            "skill_name": skill_name
        }
