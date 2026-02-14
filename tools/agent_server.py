"""Agent Server: 统一 Agent 入口、路由与编排主控。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from database.agent_runtime_store import AgentRuntimeStore
from tools.process_db_api import ProcessDBApi
from tools.agent_cli import load_config, parse_plan_from_answer, run_requirement_query
from tools.dialogue_schema_validation import DialogueSchemaValidator, ValidationResult
from tools.process_compiler import ProcessCompiler
from src.agents.evaluator_adapter import EvaluatorAdapter
from src.agents.executor_adapter import ExecutorAdapter
from src.agents.planner_adapter import PlannerAdapter
from src.control_plane.services import ConfirmationWorkflowService, OperationAuditService, PublishService

# Phase 3: ToolRegistry integration imports
from tools.registry_manager import (
    initialize_registry,
    execute_tool as execute_tool_via_registry,
    list_registered_intents,
    ToolRegistryManager,
)
from tools.agent_framework import SessionState, ChatState
import tools.agent_framework as agent_framework_pkg


server_state: Dict[str, Any] = {
    "status": "starting",
    "started_at": None,
    "config_path": "config/llm_api.json",
    "requests_total": 0,
}
workflow_runs: Dict[str, Dict[str, Any]] = {}

planner_adapter = PlannerAdapter()
evaluator_adapter = EvaluatorAdapter()
runtime_store = AgentRuntimeStore()
executor_adapter = ExecutorAdapter(runtime_store=runtime_store)
process_compiler = ProcessCompiler()
process_design_drafts: Dict[str, Dict[str, Any]] = {}
process_chat_sessions: Dict[str, List[Dict[str, str]]] = {}
process_chat_pending_ops: Dict[str, Dict[str, Any]] = {}
process_db_api = ProcessDBApi(runtime_store=runtime_store, process_design_drafts=process_design_drafts)
schema_validator = DialogueSchemaValidator()  # Phase 1: Parameter validation

# Phase 3: ToolRegistry and SessionState initialization
registry_initialized = False
session_states: Dict[str, SessionState] = {}  # session_id -> SessionState
tool_registry = None
audit_service: Optional[OperationAuditService] = None
publish_service: Optional[PublishService] = None
confirmation_service: Optional[ConfirmationWorkflowService] = None

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def init_tool_registry() -> None:
    """Initialize the ToolRegistry with all process tools"""
    global tool_registry, registry_initialized

    if registry_initialized:
        logger.info("ToolRegistry already initialized, skipping re-initialization")
        return

    try:
        tool_registry = initialize_registry(
            runtime_store=runtime_store,
            process_compiler=process_compiler,
            process_db_api=process_db_api,
            llm_service=None,  # Optional LLM service
        )
        registry_initialized = True
        logger.info("ToolRegistry initialized successfully")
        logger.info(f"Registered tools: {list(tool_registry.list_tools().keys())}")
    except Exception as e:
        logger.error(f"Failed to initialize ToolRegistry: {e}")
        registry_initialized = False
        raise


def get_or_create_session_state(session_id: str) -> SessionState:
    """Get or create SessionState for a session"""
    if session_id not in session_states:
        session_states[session_id] = SessionState(session_id=session_id)
    return session_states[session_id]


def update_session_from_tool_result(
    session_id: str, intent: str, tool_result: Dict[str, Any]
) -> None:
    """Update session state based on tool execution result"""
    session_state = get_or_create_session_state(session_id)

    status = tool_result.get("status", "unknown")

    if status == "ok":
        msg = f"执行了 {intent} 操作"
        session_state.add_message("system", msg)
        session_state.transition_to(ChatState.NORMAL)

    elif status in ["error", "validation_error"]:
        error_msg = tool_result.get("error") or tool_result.get("errors")
        error_text = str(error_msg)
        session_state.add_message("system", f"错误: {error_text}")
        session_state.transition_to(ChatState.ERROR)


def _now_iso() -> str:
    return datetime.now().isoformat()


def _get_control_plane_services() -> tuple[OperationAuditService, PublishService, ConfirmationWorkflowService]:
    global audit_service, publish_service, confirmation_service
    if audit_service is None or getattr(audit_service, "runtime_store", None) is not runtime_store:
        audit_service = OperationAuditService(runtime_store=runtime_store)
    if (
        publish_service is None
        or getattr(publish_service, "runtime_store", None) is not runtime_store
        or getattr(publish_service, "process_db_api", None) is not process_db_api
        or getattr(publish_service, "process_design_drafts", None) is not process_design_drafts
    ):
        publish_service = PublishService(
            runtime_store=runtime_store,
            process_db_api=process_db_api,
            process_design_drafts=process_design_drafts,
        )
    if (
        confirmation_service is None
        or getattr(confirmation_service, "runtime_store", None) is not runtime_store
        or getattr(confirmation_service, "publish_service", None) is not publish_service
        or getattr(confirmation_service, "audit_service", None) is not audit_service
    ):
        confirmation_service = ConfirmationWorkflowService(
            runtime_store=runtime_store,
            publish_service=publish_service,
            audit_service=audit_service,
            execute_intent_fn=lambda intent, params: _execute_process_expert_intent(intent, params),
            capture_pre_state_fn=_capture_iteration_pre_state,
            record_iteration_event_fn=_record_iteration_event_if_needed,
        )
    return audit_service, publish_service, confirmation_service


def _extract_field(text: str, patterns: List[str]) -> str:
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return str(m.group(1)).strip()
    return ""


def _extract_json_dict(text: str) -> Optional[Dict[str, Any]]:
    raw = str(text or "").strip()
    if not raw:
        return None
    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw, flags=re.IGNORECASE)
    if fence:
        candidates.append(fence.group(1))
    brace = re.search(r"(\{[\s\S]*\})", raw)
    if brace:
        candidates.append(brace.group(1))
    for item in candidates:
        try:
            obj = json.loads(item)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return None


def _is_confirmation_message(text: str) -> bool:
    s = str(text or "").strip().lower()
    if not s:
        return False
    keywords = ["确认", "执行", "同意", "开始", "ok", "yes", "go ahead"]
    return any(k in s for k in keywords)


def _build_operation_scripts(intent: str, params: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, str]:
    db_script = str(parsed.get("db_script") or "").strip()
    file_script = str(parsed.get("file_script") or "").strip()
    if not db_script:
        db_script = f"-- intent={intent}\n-- params={json.dumps(params, ensure_ascii=False)}"
    if not file_script:
        file_script = f"# file operation for {intent}\n# params={json.dumps(params, ensure_ascii=False)}"
    return {"db_script": db_script, "file_script": file_script}


def _default_process_steps() -> List[Dict[str, Any]]:
    return [
        {"step_code": "INPUT_PREP", "name": "输入准备", "tool_name": "input_prep_tool", "process_type": "自动化"},
        {"step_code": "PROCESS", "name": "工艺处理", "tool_name": "process_tool", "process_type": "自动化"},
        {"step_code": "OUTPUT_JSON", "name": "输出入库", "tool_name": "output_json_tool", "process_type": "自动化"},
    ]


def _route_request(payload: Dict[str, Any], task_spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Lightweight routing decision based on task type / risk / cost constraints.
    """
    task_spec = task_spec or {}
    context = task_spec.get("context") or payload.get("context") or {}
    constraints = task_spec.get("constraints") or payload.get("constraints") or {}
    budget = constraints.get("budget") or {}
    safety_level = str(constraints.get("safety_level") or "medium").lower()
    goal = str(task_spec.get("goal") or payload.get("requirement") or "").strip()

    domain = str(context.get("domain") or "address_governance")
    data_sources = context.get("data_sources") or []
    estimated_complexity = max(1, len(data_sources))
    if len(goal) > 120:
        estimated_complexity += 1

    gate_defaults = _load_router_gate_defaults()
    max_cost = float(budget.get("max_cost_usd") or gate_defaults["max_cost_usd"])
    max_steps = int(budget.get("max_steps") or gate_defaults["max_steps"])

    if safety_level == "high":
        route_mode = "risk_first"
        preferred_agents = ["process_expert", "planner", "evaluator", "executor"]
    elif max_cost <= 2.0:
        route_mode = "cost_guarded"
        preferred_agents = ["planner", "executor", "evaluator", "process_expert"]
    elif max_steps <= 5:
        route_mode = "latency_first"
        preferred_agents = ["planner", "executor", "evaluator", "process_expert"]
    else:
        route_mode = "balanced"
        preferred_agents = ["process_expert", "planner", "executor", "evaluator"]

    if payload.get("execution_result"):
        preferred_agent = "evaluator"
    elif payload.get("changeset"):
        preferred_agent = "executor"
    elif payload.get("task_spec"):
        preferred_agent = "planner"
    else:
        preferred_agent = preferred_agents[0]

    return {
        "route_mode": route_mode,
        "preferred_agent": preferred_agent,
        "preferred_agents": preferred_agents,
        "domain": domain,
        "safety_level": safety_level,
        "estimated_complexity": estimated_complexity,
        "budget": {
            "max_cost_usd": max_cost,
            "max_steps": max_steps,
        },
        "reason": f"mode={route_mode}, safety={safety_level}, complexity={estimated_complexity}",
    }


def _build_specialist_metadata() -> List[Dict[str, Any]]:
    """Return specialist registry metadata for routing and observability."""
    intents = sorted(list_registered_intents().keys()) if registry_initialized else []
    return [
        {
            "agent": "process_expert",
            "role": "design_and_process_control",
            "version": "1.0.0",
            "health": "ready" if registry_initialized else "degraded",
            "capabilities": ["design_process", "modify_process", "create_process", "create_version", "publish_draft"],
            "intents_registered": [i for i in intents if i in {"design_process", "modify_process", "create_process", "create_version", "publish_draft"}],
        },
        {
            "agent": "planner",
            "role": "plan_and_approval_pack",
            "version": "1.0.0",
            "health": "ready" if planner_adapter else "degraded",
            "capabilities": ["plan", "approval_pack", "changeset"],
            "intents_registered": [],
        },
        {
            "agent": "executor",
            "role": "execute_changeset",
            "version": "1.0.0",
            "health": "ready" if executor_adapter else "degraded",
            "capabilities": ["execute", "runtime_gates"],
            "intents_registered": [],
        },
        {
            "agent": "evaluator",
            "role": "evaluate_execution",
            "version": "1.0.0",
            "health": "ready" if evaluator_adapter else "degraded",
            "capabilities": ["quality_gates", "eval_report"],
            "intents_registered": [],
        },
        {
            "agent": "tool_registry",
            "role": "intent_to_tool_router",
            "version": getattr(agent_framework_pkg, "__version__", "unknown"),
            "health": "ready" if registry_initialized else "degraded",
            "capabilities": ["intent_mapping", "validation", "tool_execution"],
            "intents_registered": intents,
        },
    ]


def _extract_round_tokens(execution_result: Dict[str, Any]) -> float:
    metrics = (execution_result.get("summary") or {}).get("metrics") or {}
    return float(metrics.get("total_tokens_consumed") or 0.0)


def _safe_float(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except Exception:
        return default


def _safe_int(raw: Any, default: int) -> int:
    try:
        return int(raw)
    except Exception:
        return default


def _load_router_gate_defaults() -> Dict[str, Any]:
    defaults = {
        "max_steps": 10,
        "max_cost_usd": 5.0,
        "max_duration_sec": 900,
        "cost_per_1k_tokens_usd": 0.01,
    }
    config_path = os.getenv("FACTORY_ROUTER_GATES_PATH", "settings/router_gates.json").strip()
    cfg_file = Path(config_path)
    if not cfg_file.is_absolute():
        cfg_file = Path(__file__).resolve().parent.parent / cfg_file
    if cfg_file.exists():
        try:
            payload = json.loads(cfg_file.read_text(encoding="utf-8"))
            cfg = payload.get("defaults") if isinstance(payload, dict) else None
            if isinstance(cfg, dict):
                defaults["max_steps"] = _safe_int(cfg.get("max_steps"), defaults["max_steps"])
                defaults["max_cost_usd"] = _safe_float(cfg.get("max_cost_usd"), defaults["max_cost_usd"])
                defaults["max_duration_sec"] = _safe_int(cfg.get("max_duration_sec"), defaults["max_duration_sec"])
                defaults["cost_per_1k_tokens_usd"] = _safe_float(
                    cfg.get("cost_per_1k_tokens_usd"), defaults["cost_per_1k_tokens_usd"]
                )
        except Exception as exc:
            logger.warning("Failed to parse router gate config %s: %s", cfg_file, exc)

    defaults["max_steps"] = _safe_int(os.getenv("FACTORY_GATE_MAX_STEPS"), defaults["max_steps"])
    defaults["max_cost_usd"] = _safe_float(os.getenv("FACTORY_GATE_MAX_COST_USD"), defaults["max_cost_usd"])
    defaults["max_duration_sec"] = _safe_int(
        os.getenv("FACTORY_GATE_MAX_DURATION_SEC"), defaults["max_duration_sec"]
    )
    defaults["cost_per_1k_tokens_usd"] = _safe_float(
        os.getenv("FACTORY_GATE_COST_PER_1K_TOKENS_USD"), defaults["cost_per_1k_tokens_usd"]
    )
    return defaults


def _estimate_cost_usd(total_tokens: float, cost_per_1k_tokens_usd: Optional[float] = None) -> float:
    rate = _safe_float(cost_per_1k_tokens_usd, 0.0) if cost_per_1k_tokens_usd is not None else _load_router_gate_defaults()["cost_per_1k_tokens_usd"]
    return (float(total_tokens) / 1000.0) * rate


def _find_process_definition(process_definition_id: str = "", code: str = "") -> Optional[Dict[str, Any]]:
    return process_db_api.find_process_definition(process_definition_id=process_definition_id, code=code)


def _create_design_draft(
    requirement: str,
    process_code: str = "",
    process_name: str = "",
    domain: str = "address_governance",
    goal: str = "",
    session_id: str = "",
    draft_id: str = "",
    base_process_definition_id: str = "",
) -> Dict[str, Any]:
    cfg = load_config(str(server_state.get("config_path") or "config/llm_api.json"))
    sys_prompt = (
        "你是工艺专家Agent。请根据需求生成工艺设计草案，"
        "输出 JSON 代码块字段：auto_execute,max_duration,quality_threshold,priority,addresses。"
    )
    llm = run_requirement_query(requirement=requirement, config=cfg, system_prompt_override=sys_prompt)
    answer = llm.get("answer", "")
    plan = parse_plan_from_answer(answer)
    final_code = str(process_code or f"PROC_{uuid.uuid4().hex[:6]}").upper()
    final_name = str(process_name or f"{final_code} 工艺")
    final_draft_id = draft_id or f"draft_{uuid.uuid4().hex[:10]}"
    process_doc = "\n".join(
        [
            f"# 工艺流程文档：{final_name}",
            "",
            f"- process_code: `{final_code}`",
            f"- requirement: {requirement}",
            f"- auto_execute: {plan.get('auto_execute')}",
            f"- quality_threshold: {plan.get('quality_threshold')}",
            "## 步骤",
            "1. 输入接入与标准化",
            "2. 规则执行与门禁判定",
            "3. 输出结构化JSON与证据登记",
        ]
    )
    draft = {
        "draft_id": final_draft_id,
        "requirement": requirement,
        "process_code": final_code,
        "process_name": final_name,
        "domain": domain,
        "goal": goal or requirement,
        "plan": plan,
        "process_doc_markdown": process_doc,
        "created_at": _now_iso(),
    }
    process_design_drafts[final_draft_id] = draft
    persisted = runtime_store.upsert_process_draft(
        draft_id=final_draft_id,
        session_id=session_id,
        process_code=final_code,
        process_name=final_name,
        domain=domain,
        requirement=requirement,
        goal=goal or requirement,
        plan=plan,
        process_doc_markdown=process_doc,
        llm_answer=answer,
        base_process_definition_id=base_process_definition_id or None,
        status="editable",
    )
    draft.update({"updated_at": persisted.get("updated_at"), "draft_status": persisted.get("status", "editable")})

    # Compile process: extract metadata, identify steps, generate tools
    compile_result = process_compiler.compile(draft, session_id=session_id)

    result = {**draft, "llm_answer": answer}
    result["status"] = "ok"

    # Include compilation results
    result["compilation"] = {
        "success": compile_result.success,
        "process_code": compile_result.process_code,
        "process_spec": compile_result.process_spec,
        "tool_scripts": compile_result.tool_scripts,
        "tool_metadata": compile_result.tool_metadata,
        "execution_readiness": compile_result.execution_readiness,
        "validation_errors": compile_result.validation_errors,
        "validation_warnings": compile_result.validation_warnings,
    }

    return result


def _publish_draft(draft_id: str, reason: str = "", operator: str = "", source: str = "") -> Dict[str, Any]:
    _, publish_svc, _ = _get_control_plane_services()
    return publish_svc.publish_draft(draft_id=draft_id, reason=reason, operator=operator, source=source)


def _attach_publish_audit(
    tool_result: Dict[str, Any],
    draft_id: str,
    reason: str = "",
    operator: str = "",
    source: str = "",
    confirmation_id: str = "",
    confirmer_user_id: str = "",
    latency_ms: Optional[int] = None,
) -> Dict[str, Any]:
    _, publish_svc, _ = _get_control_plane_services()
    return publish_svc.attach_publish_audit(
        tool_result=tool_result,
        draft_id=draft_id,
        reason=reason,
        operator=operator,
        source=source,
        confirmation_id=confirmation_id,
        confirmer_user_id=confirmer_user_id,
        latency_ms=latency_ms,
    )


def _log_operation_audit(
    operation_type: str,
    operation_status: str,
    operation_id: str = "",
    actor: str = "",
    source: str = "",
    confirmation_id: str = "",
    confirmer_user_id: str = "",
    session_id: str = "",
    draft_id: str = "",
    process_definition_id: str = "",
    process_version_id: str = "",
    task_run_id: str = "",
    error_code: str = "",
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    audit_svc, _, _ = _get_control_plane_services()
    audit_svc.log(
        operation_type=operation_type,
        operation_status=operation_status,
        operation_id=operation_id,
        actor=actor,
        source=source,
        confirmation_id=confirmation_id,
        confirmer_user_id=confirmer_user_id,
        session_id=session_id,
        draft_id=draft_id,
        process_definition_id=process_definition_id,
        process_version_id=process_version_id,
        task_run_id=task_run_id,
        error_code=error_code,
        detail=detail or {},
    )


def _get_process_definition_snapshot(process_definition_id: str) -> Optional[Dict[str, Any]]:
    items = runtime_store.list_process_definitions()
    return next((x for x in items if str(x.get("id") or "") == process_definition_id), None)


def _resolve_process_definition_id(params: Dict[str, Any], tool_result: Dict[str, Any]) -> str:
    process_definition_id = str(params.get("process_definition_id") or "").strip()
    if process_definition_id:
        return process_definition_id

    result_definition_id = str(tool_result.get("process_definition_id") or "").strip()
    if result_definition_id:
        return result_definition_id

    process_version = tool_result.get("process_version") if isinstance(tool_result, dict) else None
    if isinstance(process_version, dict):
        from_version = str(process_version.get("process_definition_id") or "").strip()
        if from_version:
            return from_version

    process_definition = tool_result.get("process_definition") if isinstance(tool_result, dict) else None
    if isinstance(process_definition, dict):
        from_definition = str(process_definition.get("id") or "").strip()
        if from_definition:
            return from_definition

    code = str(params.get("code") or "").strip().upper()
    if not code:
        draft_id = str(params.get("draft_id") or "").strip()
        if draft_id:
            draft = runtime_store.get_process_draft(draft_id)
            code = str((draft or {}).get("process_code") or "").strip().upper()
    if not code:
        return ""
    hit = _find_process_definition(code=code)
    return str((hit or {}).get("id") or "")


def _resolve_version_by_id(process_definition_id: str, version_id: str) -> str:
    if not process_definition_id or not version_id:
        return ""
    versions = runtime_store.list_process_versions(process_definition_id)
    hit = next((x for x in versions if str(x.get("id") or "") == version_id), None)
    return str((hit or {}).get("version") or "")


def _capture_iteration_pre_state(intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Capture pre-operation version snapshot for iteration event accuracy."""
    if intent not in {"create_version", "publish_draft"}:
        return {}
    process_definition_id = _resolve_process_definition_id(params=params, tool_result={})
    if not process_definition_id:
        return {}
    snap = _get_process_definition_snapshot(process_definition_id) or {}
    from_version_id = str(snap.get("current_version_id") or "").strip()
    return {
        "_process_definition_id": process_definition_id,
        "_from_version_id": from_version_id,
        "_from_version": _resolve_version_by_id(process_definition_id, from_version_id),
    }


def _record_iteration_event_if_needed(
    intent: str,
    params: Dict[str, Any],
    tool_result: Dict[str, Any],
) -> Optional[str]:
    if intent not in {"create_version", "publish_draft"}:
        return None
    if not isinstance(tool_result, dict) or tool_result.get("status") != "ok":
        return None

    process_definition_id = _resolve_process_definition_id(params=params, tool_result=tool_result)
    if not process_definition_id:
        return None

    from_version_id = str(params.get("_from_version_id") or "").strip()
    from_version = str(params.get("_from_version") or "").strip()
    if not from_version_id:
        current_snapshot = _get_process_definition_snapshot(process_definition_id) or {}
        current_version_id = str(current_snapshot.get("current_version_id") or "").strip()
        from_version_id = current_version_id
        from_version = _resolve_version_by_id(process_definition_id, from_version_id)

    process_version = tool_result.get("process_version") if isinstance(tool_result, dict) else None
    to_version_id = ""
    to_version = ""
    if isinstance(process_version, dict):
        to_version_id = str(process_version.get("id") or "").strip()
        to_version = str(process_version.get("version") or "").strip()
    else:
        to_version_id = str(tool_result.get("process_version_id") or "").strip()
        to_version = str(tool_result.get("version") or "").strip()

    # If operation published a new current version and pre-op snapshot is missing,
    # infer previous version from history as best effort.
    if to_version_id and from_version_id == to_version_id and not str(params.get("_from_version_id") or "").strip():
        versions = runtime_store.list_process_versions(process_definition_id)
        previous = next((v for v in versions if str(v.get("id") or "") != to_version_id), None)
        if previous:
            from_version_id = str(previous.get("id") or "")
            from_version = str(previous.get("version") or "")

    reason = str(params.get("reason") or "").strip()
    if not reason:
        reason = f"{intent} via agent_server"

    try:
        return runtime_store.record_process_iteration_event(
            process_definition_id=process_definition_id,
            from_version_id=from_version_id or None,
            from_version=from_version or None,
            to_version_id=to_version_id or None,
            to_version=to_version or None,
            trigger_type=intent,
            strategy_patch={
                "intent": intent,
                "params": params,
                "result_meta": {
                    "status": tool_result.get("status"),
                    "intent": tool_result.get("intent"),
                },
            },
            reason=reason,
        )
    except Exception as exc:
        logger.warning("Failed to record process iteration event: %s", exc)
        return None


def _execute_process_expert_intent(intent: str, params: Dict[str, Any], session_id: str = "") -> Dict[str, Any]:
    """
    Execute process expert intent using ToolRegistry.

    Refactored to use ToolRegistry instead of hardcoded if-elif.
    All tool routing now handled by registry.
    """
    if not registry_initialized or tool_registry is None:
        return {
            "status": "error",
            "error": "ToolRegistry not initialized",
            "intent": intent,
        }

    try:
        result = execute_tool_via_registry(intent, params, session_id=session_id)

        # Ensure backward compatibility - add intent to response
        if isinstance(result, dict):
            result.setdefault("intent", intent)

        return result

    except Exception as e:
        logger.error(f"Tool execution failed for intent={intent}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "intent": intent,
            "error_type": "execution_error",
        }


def _run_process_expert_chat_turn(session_id: str, user_message: str) -> Dict[str, Any]:
    history = process_chat_sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": user_message})
    runtime_store.append_process_chat_turn(session_id=session_id, role="user", content=user_message)

    pending = process_chat_pending_ops.get(session_id)
    if pending and _is_confirmation_message(user_message):
        # Phase 1: Use structured confirmation instead of keyword matching
        confirmation_id = pending.get("confirmation_id")
        pending_params = dict(pending.get("params") or {})
        confirmation = {
            "operation_type": str(pending.get("intent") or ""),
            "operation_params": pending_params,
            "session_id": session_id,
            "draft_id": str((pending_params or {}).get("draft_id") or ""),
        }
        _, _, confirm_svc = _get_control_plane_services()
        tool_result = confirm_svc.execute_confirmed(
            confirmation=confirmation,
            confirmation_id=str(confirmation_id or f"chat_confirm_{uuid.uuid4().hex[:8]}"),
            confirmer_user_id="user",
            source="process_expert_chat",
            actor="chat_pending_confirmation",
            execute_intent_fn=lambda intent, params: _execute_process_expert_intent(intent, params, session_id=session_id),
        )
        update_session_from_tool_result(session_id, pending["intent"], tool_result)
        assistant_message = "已收到确认并执行数据库操作。"
        history.append({"role": "assistant", "content": assistant_message})
        runtime_store.append_process_chat_turn(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
            draft_id=str((pending.get("params") or {}).get("draft_id") or ""),
        )
        process_chat_pending_ops.pop(session_id, None)
        return {
            "status": "ok",
            "action": "chat",
            "session_id": session_id,
            "assistant_message": assistant_message,
            "intent": pending["intent"],
            "execute": True,
            "tool_result": tool_result,
            "operation_scripts": pending.get("operation_scripts", {}),
            "timestamp": _now_iso(),
        }

    recent = history[-8:]
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
    defs = runtime_store.list_process_definitions()[:20]
    defs_text = "\n".join([f"- {x.get('code')} ({x.get('id')})" for x in defs]) or "- 暂无工艺"
    parser_prompt = (
        "你是工艺专家Agent的意图解析器。"
        "请将用户自然语言解析为 JSON，不要输出任何额外文本。"
        "JSON格式："
        '{"intent":"design_process|modify_process|create_process|create_version|publish_draft|query_process|query_version|query_process_tasks|query_task_io|chat",'
        '"execute":false,"params":{},"assistant_reply":"给用户的自然语言回复","db_script":"SQL或伪SQL脚本","file_script":"文件脚本"}。'
        "默认 execute=false，只有用户明确要求执行数据库操作时才返回 true。"
        "重要：对于 design_process 和 create_process，\"code\"字段可以省略（会自动生成），重点提取 name/goal/domain 等参数。"
        "如果无法确定，intent=chat。"
    )
    requirement = (
        f"当前工艺列表:\n{defs_text}\n\n"
        f"会话历史:\n{history_text}\n\n"
        f"用户本轮输入:\n{user_message}"
    )
    cfg = load_config(str(server_state.get("config_path") or "config/llm_api.json"))
    llm = run_requirement_query(requirement=requirement, config=cfg, system_prompt_override=parser_prompt)
    answer = llm.get("answer", "")
    parsed = _extract_json_dict(answer) or {}
    intent = str(parsed.get("intent") or "chat").strip()
    params = parsed.get("params") if isinstance(parsed.get("params"), dict) else {}
    execute = bool(parsed.get("execute"))

    # Phase 1: Validate parameters using schema validator
    validation_result: ValidationResult = schema_validator.validate(intent, params)
    if not validation_result.is_valid and intent not in {"chat", "design_process", "modify_process"}:
        # Log validation failure and return error
        runtime_store.log_parsing_event(
            session_id=session_id,
            raw_llm_response=answer,
            parsed_json=json.dumps(params, ensure_ascii=False),
            validation_status="invalid",
            validation_errors=json.dumps(validation_result.errors, ensure_ascii=False),
        )
        assistant_message = f"参数验证失败：{'; '.join(validation_result.errors)}"
        history.append({"role": "assistant", "content": assistant_message})
        runtime_store.append_process_chat_turn(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
        )
        return {
            "status": "validation_error",
            "action": "chat",
            "session_id": session_id,
            "assistant_message": assistant_message,
            "intent": intent,
            "validation_errors": validation_result.errors,
            "timestamp": _now_iso(),
        }

    # Use sanitized parameters
    params = validation_result.sanitized_params

    # Auto-generate process code if not provided for design_process or create_process
    if intent in {"design_process", "create_process"} and not (params.get("process_code") or params.get("code")):
        # Generate code from process name or user message
        base_name = str(params.get("process_name") or "").strip() or user_message.split("\\n")[0][:30]
        # Extract first few characters from Chinese/English and convert to uppercase
        code_base = "".join([c for c in base_name if c.isalnum() or c.isascii()])[:20].upper()
        if not code_base:
            code_base = "PROC"
        # Add timestamp suffix to ensure uniqueness
        import time
        timestamp_suffix = str(int(time.time() * 1000) % 100000)[-5:]
        generated_code = f"{code_base}_{timestamp_suffix}"
        params["code"] = generated_code
        params["process_code"] = generated_code

    operation_scripts = _build_operation_scripts(intent, params, parsed)
    session_draft = runtime_store.get_latest_editable_draft_by_session(session_id)

    if intent in {"design_process", "modify_process"}:
        if not execute:
            base_draft_id = str((session_draft or {}).get("draft_id") or "")
            base_process_definition_id = str((session_draft or {}).get("base_process_definition_id") or "")
            tool_draft = _create_design_draft(
                requirement=str(params.get("requirement") or user_message),
                process_code=str(params.get("process_code") or params.get("code") or (session_draft or {}).get("process_code") or ""),
                process_name=str(params.get("process_name") or (session_draft or {}).get("process_name") or ""),
                domain=str(params.get("domain") or (session_draft or {}).get("domain") or "address_governance"),
                goal=str(params.get("goal") or params.get("change_request") or ""),
                session_id=session_id,
                draft_id=base_draft_id,
                base_process_definition_id=base_process_definition_id,
            )
            tool_result = {"status": "ok", "intent": intent, "draft": tool_draft}
        else:
            # 设计/修改动作不直接写发布表；即使execute=true也保持草案更新语义。
            tool_draft = _create_design_draft(
                requirement=str(params.get("requirement") or user_message),
                process_code=str(params.get("process_code") or params.get("code") or (session_draft or {}).get("process_code") or ""),
                process_name=str(params.get("process_name") or (session_draft or {}).get("process_name") or ""),
                domain=str(params.get("domain") or (session_draft or {}).get("domain") or "address_governance"),
                goal=str(params.get("goal") or params.get("change_request") or ""),
                session_id=session_id,
                draft_id=str((session_draft or {}).get("draft_id") or ""),
                base_process_definition_id=str((session_draft or {}).get("base_process_definition_id") or ""),
            )
            tool_result = {"status": "ok", "intent": intent, "draft": tool_draft}
    else:
        write_intents = {"create_process", "create_version", "publish_draft"}
        if intent in write_intents and not execute:
            _, _, confirm_svc = _get_control_plane_services()
            tool_result = confirm_svc.create_pending_confirmation(
                session_id=session_id,
                intent=intent,
                params=params,
                expires_in_sec=900,
                source="process_expert_chat",
            )
            confirmation_id = str(tool_result.get("confirmation_id") or "")
            process_chat_pending_ops[session_id] = {
                "intent": intent,
                "params": params,
                "operation_scripts": operation_scripts,
                "confirmation_id": confirmation_id,
            }
        else:
            params_for_execution = dict(params)
            params_for_event = dict(params_for_execution)
            pre_state = _capture_iteration_pre_state(intent, params_for_event)
            if pre_state:
                params_for_event.update(pre_state)
            tool_result = _execute_process_expert_intent(intent, params_for_execution, session_id=session_id)
            _record_iteration_event_if_needed(
                intent=intent,
                params=params_for_event,
                tool_result=tool_result if isinstance(tool_result, dict) else {},
            )
            if isinstance(tool_result, dict):
                _log_operation_audit(
                    operation_type=intent,
                    operation_status=str(tool_result.get("status") or "unknown").lower(),
                    actor="system",
                    source="process_expert_chat",
                    session_id=session_id,
                    draft_id=str((params_for_execution or {}).get("draft_id") or ""),
                    process_definition_id=str(tool_result.get("process_definition_id") or ""),
                    process_version_id=str(tool_result.get("process_version_id") or ""),
                    error_code=str(tool_result.get("error") or ""),
                    detail={"path": "chat_direct_execute"},
                )
            update_session_from_tool_result(session_id, intent, tool_result)
            if intent in write_intents:
                process_chat_pending_ops.pop(session_id, None)
    assistant_message = str(parsed.get("assistant_reply") or "").strip()
    if not assistant_message:
        if tool_result.get("status") == "pending_confirmation":
            assistant_message = "我已整理操作方案和脚本，回复“确认执行”后我会写入数据库。"
        elif tool_result.get("status") == "ok":
            assistant_message = f"已完成操作：{intent}"
        else:
            assistant_message = f"执行失败：{tool_result.get('error', 'unknown')}"
    history.append({"role": "assistant", "content": assistant_message})
    runtime_store.append_process_chat_turn(
        session_id=session_id,
        role="assistant",
        content=assistant_message,
        draft_id=str(((tool_result.get("draft") or {}).get("draft_id") if isinstance(tool_result, dict) else "") or ""),
    )
    return {
        "status": "ok",
        "action": "chat",
        "session_id": session_id,
        "assistant_message": assistant_message,
        "intent": intent,
        "execute": execute,
        "tool_result": tool_result,
        "operation_scripts": operation_scripts,
        "llm_parser_answer": answer,
        "timestamp": _now_iso(),
    }


def _process_expert_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    requirement = str(payload.get("requirement") or "").strip()
    if not requirement:
        return {"status": "error", "error": "requirement 不能为空"}

    cfg = load_config(str(server_state.get("config_path") or "config/llm_api.json"))
    context = payload.get("context") or {}
    context_text = json.dumps(context, ensure_ascii=False) if context else "{}"
    system_prompt = (
        "你是数据工厂工艺专家。"
        "请针对需求给出可执行方案，并尽可能返回 JSON 代码块，字段包含："
        "auto_execute,max_duration,quality_threshold,priority,addresses。"
        f"上下文：{context_text}"
    )
    result = run_requirement_query(
        requirement=requirement,
        config=cfg,
        system_prompt_override=system_prompt,
    )
    plan = parse_plan_from_answer(result.get("answer", ""))
    return {
        "status": "ok",
        "agent_type": "process_expert",
        "request_id": result.get("request_id", ""),
        "model": result.get("model", ""),
        "answer": result.get("answer", ""),
        "plan": plan,
        "timestamp": _now_iso(),
    }


def _planner_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    task_spec = payload.get("task_spec") or {}
    if not task_spec or not task_spec.get("task_id"):
        return {"status": "error", "error": "task_spec.task_id 不能为空"}
    plan, approval_pack = planner_adapter.plan(task_spec)
    changeset = planner_adapter.build_changeset(task_spec, plan, approval_pack)
    return {
        "status": "ok",
        "agent_type": "planner",
        "task_id": task_spec["task_id"],
        "plan": plan,
        "approval_pack": approval_pack,
        "changeset": changeset,
        "timestamp": _now_iso(),
    }


def _executor_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    task_spec = payload.get("task_spec") or {}
    changeset = payload.get("changeset") or {}
    approvals = payload.get("approvals") or []
    if not task_spec or not task_spec.get("task_id"):
        return {"status": "error", "error": "task_spec.task_id 不能为空"}
    if not changeset:
        return {"status": "error", "error": "changeset 不能为空"}
    execution_result = executor_adapter.execute(task_spec, changeset, approvals=approvals)
    return {
        "status": "ok",
        "agent_type": "executor",
        "task_id": task_spec["task_id"],
        "execution_result": execution_result,
        "timestamp": _now_iso(),
    }


def _evaluator_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    task_spec = payload.get("task_spec") or {}
    changeset = payload.get("changeset") or {}
    execution_result = payload.get("execution_result") or {}
    if not task_spec or not task_spec.get("task_id"):
        return {"status": "error", "error": "task_spec.task_id 不能为空"}
    if not changeset:
        return {"status": "error", "error": "changeset 不能为空"}
    if not execution_result:
        return {"status": "error", "error": "execution_result 不能为空"}
    eval_report = evaluator_adapter.evaluate(task_spec, changeset, execution_result)
    return {
        "status": "ok",
        "agent_type": "evaluator",
        "task_id": task_spec["task_id"],
        "eval_report": eval_report,
        "timestamp": _now_iso(),
    }


def _make_task_spec_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    explicit = payload.get("task_spec")
    if isinstance(explicit, dict) and explicit.get("task_id"):
        return explicit
    requirement = str(payload.get("requirement") or "").strip()
    if not requirement:
        requirement = "通用工艺任务"
    task_id = payload.get("task_id") or f"task_{uuid.uuid4().hex[:8]}"
    context = payload.get("context") or {
        "domain": "address_governance",
        "data_sources": ["ods_address_raw"],
        "target_platform": "airflow",
    }
    constraints = payload.get("constraints") or {
        "env": "dev",
        "budget": {"max_steps": 10, "max_cost_usd": 5},
        "safety_level": "medium",
    }
    return {
        "task_id": task_id,
        "tenant_id": str(payload.get("tenant_id") or "tenant_default"),
        "goal": requirement,
        "context": context,
        "constraints": constraints,
    }


def _extract_strategy_patch(execution_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    task_exec = (
        execution_result.get("workflow_result", {})
        .get("stages", {})
        .get("task_executions", {})
    ) or {}
    return list(task_exec.get("strategy_patch", []) or [])


def _extract_unverifiable_count(execution_result: Dict[str, Any]) -> int:
    task_exec = (
        execution_result.get("workflow_result", {})
        .get("stages", {})
        .get("task_executions", {})
    ) or {}
    return len(task_exec.get("unverifiable_online_list", []) or [])


def _build_iteration_decision(
    eval_report: Dict[str, Any],
    round_index: int,
    max_rounds: int,
    current_unverifiable: int,
    previous_unverifiable: int,
) -> Dict[str, Any]:
    if round_index >= max_rounds:
        return {"should_continue": False, "stop_reason": "BUDGET_EXHAUSTED"}
    if eval_report.get("status") == "FAIL":
        return {"should_continue": False, "stop_reason": "EVALUATOR_FAIL"}
    if current_unverifiable <= 0:
        return {"should_continue": False, "stop_reason": "NO_UNRESOLVED_CASE"}
    gain = max(0, previous_unverifiable - current_unverifiable)
    if previous_unverifiable > 0 and gain == 0:
        return {"should_continue": False, "stop_reason": "NO_GAIN"}
    return {"should_continue": True, "stop_reason": None}


def _run_orchestrated_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    task_spec_base = _make_task_spec_from_payload(payload)
    router_decision = _route_request(payload, task_spec_base)
    task_spec_base.setdefault("context", {})
    task_spec_base["context"]["router_decision"] = router_decision
    workflow_id = str(payload.get("workflow_id") or f"wf_{uuid.uuid4().hex[:12]}")
    max_rounds = int(payload.get("max_rounds", 3) or 3)
    constraints = task_spec_base.get("constraints") or {}
    budget = constraints.get("budget") or {}
    gate_defaults = _load_router_gate_defaults()
    max_steps_budget = int(budget.get("max_steps") or gate_defaults["max_steps"])
    max_cost_usd = float(budget.get("max_cost_usd") or gate_defaults["max_cost_usd"])
    max_duration_sec = int(constraints.get("max_duration_sec") or payload.get("max_duration_sec") or gate_defaults["max_duration_sec"])
    cost_per_1k_tokens_usd = float(
        constraints.get("cost_per_1k_tokens_usd") or gate_defaults["cost_per_1k_tokens_usd"]
    )
    if max_rounds > max_steps_budget:
        return {
            "status": "error",
            "error": f"ROUTER_GATE_MAX_STEPS_EXCEEDED: max_rounds={max_rounds} > max_steps={max_steps_budget}",
            "router_decision": router_decision,
            "gate": {"pass": False, "code": "ROUTER_GATE_MAX_STEPS_EXCEEDED"},
        }
    process_code = str(payload.get("process_code") or "ADDR_GOV_AND_GRAPH_COMBINED")
    process_info = runtime_store.get_released_process(process_code)
    if not process_info:
        return {"status": "error", "error": f"process_code 不存在或未发布: {process_code}"}

    input_snapshot_ref = f"file://runtime_store/tasks/{workflow_id}/input/"
    task_run_id = runtime_store.create_task_run(
        task_id=task_spec_base["task_id"],
        process_definition_id=process_info["process_definition_id"],
        process_version_id=process_info["process_version_id"],
        max_rounds=max_rounds,
        input_snapshot_ref=input_snapshot_ref,
    )
    if payload.get("inputs"):
        for item in payload.get("inputs", []):
            text = json.dumps(item, ensure_ascii=False)
            runtime_store.add_task_input(
                task_run_id=task_run_id,
                input_type=str(item.get("type") or "text"),
                source_uri=str(item.get("source_uri") or "inline_input"),
                mime_type=str(item.get("mime_type") or "application/json"),
                content=text.encode("utf-8"),
                metadata={"origin": "workflow_start_payload"},
            )
    else:
        runtime_store.add_task_input(
            task_run_id=task_run_id,
            input_type="text",
            source_uri="inline_requirement",
            mime_type="text/plain",
            content=str(payload.get("requirement") or task_spec_base.get("goal") or "").encode("utf-8"),
            metadata={"origin": "workflow_start_requirement"},
        )

    rounds: List[Dict[str, Any]] = []
    status = "running"
    strategy_patch: List[Dict[str, Any]] = []
    prev_unverifiable = 10**9
    final_reason = None
    started_at = time.time()
    accumulated_tokens = 0.0

    for round_index in range(1, max_rounds + 1):
        task_spec = json.loads(json.dumps(task_spec_base, ensure_ascii=False))
        task_spec["task_id"] = f"{task_spec_base['task_id']}_r{round_index}"
        task_spec.setdefault("context", {})
        task_spec["context"]["task_run_id"] = task_run_id
        task_spec["context"]["workflow_id"] = workflow_id
        if strategy_patch:
            task_spec["context"]["strategy_patch"] = strategy_patch

        runtime_store.add_step_run(
            task_run_id=task_run_id,
            step_code="PLANNER",
            round_index=round_index,
            status="running",
        )
        plan, approval_pack = planner_adapter.plan(task_spec)
        if strategy_patch:
            extra = planner_adapter.plan_from_strategy_patch(strategy_patch)
            if extra:
                plan["steps"] = extra + plan.get("steps", [])
        changeset = planner_adapter.build_changeset(task_spec, plan, approval_pack)
        runtime_store.add_step_run(
            task_run_id=task_run_id,
            step_code="PLANNER",
            round_index=round_index,
            status="completed",
        )
        approvals = [item["type"] for item in approval_pack.get("items", []) if item.get("blocking", True)]
        runtime_store.add_step_run(
            task_run_id=task_run_id,
            step_code="EXECUTOR",
            round_index=round_index,
            status="running",
        )
        execution_result = executor_adapter.execute(task_spec, changeset, approvals=approvals)
        round_tokens = _extract_round_tokens(execution_result)
        accumulated_tokens += round_tokens
        estimated_cost_usd = _estimate_cost_usd(accumulated_tokens, cost_per_1k_tokens_usd)
        runtime_store.add_step_run(
            task_run_id=task_run_id,
            step_code="EXECUTOR",
            round_index=round_index,
            status="completed" if execution_result.get("status") == "PASS" else "failed",
            error_code=None if execution_result.get("status") == "PASS" else "EXECUTION_FAIL",
            error_detail=execution_result.get("stage"),
        )
        runtime_store.add_step_run(
            task_run_id=task_run_id,
            step_code="EVALUATOR",
            round_index=round_index,
            status="running",
        )
        eval_report = evaluator_adapter.evaluate(task_spec, changeset, execution_result)
        runtime_store.add_step_run(
            task_run_id=task_run_id,
            step_code="EVALUATOR",
            round_index=round_index,
            status="completed" if eval_report.get("status") == "PASS" else "failed",
            error_code=None if eval_report.get("status") == "PASS" else "EVAL_FAIL",
            error_detail=eval_report.get("status"),
        )

        current_unverifiable = _extract_unverifiable_count(execution_result)
        decision = _build_iteration_decision(
            eval_report=eval_report,
            round_index=round_index,
            max_rounds=max_rounds,
            current_unverifiable=current_unverifiable,
            previous_unverifiable=prev_unverifiable if prev_unverifiable < 10**8 else current_unverifiable + 1,
        )
        prev_unverifiable = current_unverifiable
        strategy_patch = _extract_strategy_patch(execution_result)

        round_result = {
            "round": round_index,
            "task_id": task_spec["task_id"],
            "router_decision": router_decision,
            "plan_id": plan.get("plan_id"),
            "execution_status": execution_result.get("status"),
            "eval_status": eval_report.get("status"),
            "tokens_consumed_round": round_tokens,
            "tokens_consumed_total": accumulated_tokens,
            "estimated_cost_usd_total": estimated_cost_usd,
            "decision": decision,
            "unverifiable_online_count": current_unverifiable,
            "strategy_patch": strategy_patch,
            "execution_result": execution_result,
            "eval_report": eval_report,
        }
        rounds.append(round_result)
        runtime_store.add_output_json(
            task_run_id=task_run_id,
            output_type=f"round_{round_index}",
            content=round_result,
            schema_version="v1",
        )

        elapsed_sec = int(time.time() - started_at)
        if estimated_cost_usd > max_cost_usd:
            status = "failed"
            final_reason = "ROUTER_GATE_COST_BUDGET_EXCEEDED"
            break
        if elapsed_sec > max_duration_sec:
            status = "failed"
            final_reason = "ROUTER_GATE_TIMEOUT_EXCEEDED"
            break

        if not decision.get("should_continue"):
            status = "completed" if eval_report.get("status") != "FAIL" else "failed"
            final_reason = decision.get("stop_reason")
            break

    if status == "running":
        status = "completed"
        final_reason = "MAX_ROUNDS_REACHED"

    final_payload = {
        "status": "ok",
        "workflow_id": workflow_id,
        "task_run_id": task_run_id,
        "process_code": process_code,
        "process_definition_id": process_info["process_definition_id"],
        "process_version_id": process_info["process_version_id"],
        "task_id_base": task_spec_base["task_id"],
        "router_decision": router_decision,
        "budget_gate": {
            "max_steps": max_steps_budget,
            "max_cost_usd": max_cost_usd,
            "max_duration_sec": max_duration_sec,
            "cost_per_1k_tokens_usd": cost_per_1k_tokens_usd,
            "accumulated_tokens": accumulated_tokens,
            "estimated_cost_usd": _estimate_cost_usd(accumulated_tokens, cost_per_1k_tokens_usd),
        },
        "orchestrator_status": status,
        "final_reason": final_reason,
        "rounds": rounds,
        "latest": rounds[-1] if rounds else {},
        "timestamp": _now_iso(),
    }
    final_output_id = runtime_store.add_output_json(
        task_run_id=task_run_id,
        output_type="final",
        content=final_payload,
        schema_version="v1",
    )
    runtime_store.update_task_run(
        task_run_id=task_run_id,
        status=status,
        current_round=len(rounds),
        output_snapshot_ref=f"sqlite://task_output_json/{final_output_id}",
        ended=True,
    )
    workflow_runs[workflow_id] = final_payload
    return final_payload


AGENT_HANDLERS = {
    "process_expert": _process_expert_handler,
    "planner": _planner_handler,
    "executor": _executor_handler,
    "evaluator": _evaluator_handler,
}


class AgentServerHandler(BaseHTTPRequestHandler):
    """HTTP 处理器。"""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_json(
                {
                    "status": "ok",
                    "server_status": server_state.get("status", "unknown"),
                    "started_at": server_state.get("started_at"),
                    "requests_total": server_state.get("requests_total", 0),
                    "config_path": server_state.get("config_path"),
                }
            )
            return
        if parsed.path == "/process-console":
            tpl = Path(__file__).resolve().parent.parent / "templates" / "process_console.html"
            if tpl.exists():
                html = tpl.read_text(encoding="utf-8")
            else:
                html = "<html><body><h1>process console not found</h1></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return
        if parsed.path == "/api/v1/process/definitions":
            self._send_json({"status": "ok", "items": runtime_store.list_process_definitions()})
            return
        if parsed.path == "/api/v1/process/versions":
            qs = parse_qs(parsed.query)
            process_definition_id = (qs.get("process_definition_id", [""])[0] or "").strip()
            if not process_definition_id:
                self._send_json({"status": "error", "error": "process_definition_id 不能为空"}, status=400)
                return
            self._send_json({"status": "ok", "items": runtime_store.list_process_versions(process_definition_id)})
            return
        if parsed.path == "/api/v1/process/iterations":
            qs = parse_qs(parsed.query)
            process_definition_id = (qs.get("process_definition_id", [""])[0] or "").strip()
            if not process_definition_id:
                self._send_json({"status": "error", "error": "process_definition_id 不能为空"}, status=400)
                return
            limit = int((qs.get("limit", ["100"])[0] or "100"))
            trigger_type = (qs.get("trigger_type", [""])[0] or "").strip()
            items = runtime_store.list_process_iteration_events(
                process_definition_id=process_definition_id,
                limit=limit,
                trigger_type=trigger_type,
            )
            self._send_json({"status": "ok", "items": items})
            return
        if parsed.path == "/api/v1/router/decision":
            qs = parse_qs(parsed.query)
            budget: Dict[str, Any] = {}
            max_cost_raw = (qs.get("max_cost_usd", [""])[0] or "").strip()
            max_steps_raw = (qs.get("max_steps", [""])[0] or "").strip()
            if max_cost_raw:
                budget["max_cost_usd"] = _safe_float(max_cost_raw, 5.0)
            if max_steps_raw:
                budget["max_steps"] = _safe_int(max_steps_raw, 10)
            payload = {
                "requirement": (qs.get("requirement", [""])[0] or "").strip(),
                "context": {"domain": (qs.get("domain", ["address_governance"])[0] or "address_governance").strip()},
                "constraints": {
                    "safety_level": (qs.get("safety_level", ["medium"])[0] or "medium").strip(),
                    "budget": budget,
                },
            }
            decision = _route_request(payload=payload, task_spec=_make_task_spec_from_payload(payload))
            self._send_json({"status": "ok", "router_decision": decision})
            return
        if parsed.path == "/api/v1/agents/specialists":
            self._send_json({"status": "ok", "items": _build_specialist_metadata()})
            return
        if parsed.path == "/api/v1/external-api/calls":
            qs = parse_qs(parsed.query)
            task_run_id = (qs.get("task_run_id", [""])[0] or "").strip()
            api_name = (qs.get("api_name", [""])[0] or "").strip()
            limit = int((qs.get("limit", ["100"])[0] or "100"))
            items = runtime_store.list_api_call_logs(task_run_id=task_run_id, api_name=api_name, limit=limit)
            self._send_json({"status": "ok", "items": items})
            return
        if parsed.path == "/api/v1/confirmations":
            qs = parse_qs(parsed.query)
            confirmation_status = (qs.get("status", [""])[0] or "").strip()
            operation_type = (qs.get("operation_type", [""])[0] or "").strip()
            session_id = (qs.get("session_id", [""])[0] or "").strip()
            limit = _safe_int((qs.get("limit", ["100"])[0] or "100"), 100)
            items = runtime_store.list_confirmation_records(
                confirmation_status=confirmation_status,
                operation_type=operation_type,
                session_id=session_id,
                limit=limit,
            )
            self._send_json({"status": "ok", "items": items})
            return
        if parsed.path == "/api/v1/operation-audits":
            qs = parse_qs(parsed.query)
            operation_type = (qs.get("operation_type", [""])[0] or "").strip()
            operation_status = (qs.get("operation_status", [""])[0] or "").strip()
            confirmation_id = (qs.get("confirmation_id", [""])[0] or "").strip()
            draft_id = (qs.get("draft_id", [""])[0] or "").strip()
            session_id = (qs.get("session_id", [""])[0] or "").strip()
            limit = _safe_int((qs.get("limit", ["100"])[0] or "100"), 100)
            items = runtime_store.list_operation_audits(
                operation_type=operation_type,
                operation_status=operation_status,
                confirmation_id=confirmation_id,
                draft_id=draft_id,
                session_id=session_id,
                limit=limit,
            )
            self._send_json({"status": "ok", "items": items})
            return
        if parsed.path == "/api/v1/process/tasks":
            qs = parse_qs(parsed.query)
            process_definition_id = (qs.get("process_definition_id", [""])[0] or "").strip()
            if not process_definition_id:
                self._send_json({"status": "error", "error": "process_definition_id 不能为空"}, status=400)
                return
            self._send_json({"status": "ok", "items": runtime_store.list_tasks_by_process_definition(process_definition_id)})
            return
        if parsed.path == "/api/v1/process/draft":
            qs = parse_qs(parsed.query)
            draft_id = (qs.get("draft_id", [""])[0] or "").strip()
            if not draft_id:
                self._send_json({"status": "error", "error": "draft_id 不能为空"}, status=400)
                return
            item = runtime_store.get_process_draft(draft_id)
            if not item:
                self._send_json({"status": "error", "error": "draft_id 不存在", "draft_id": draft_id}, status=404)
                return
            self._send_json({"status": "ok", "draft": item})
            return
        if parsed.path.startswith("/api/v1/draft/") and parsed.path.endswith("/compare"):
            self._handle_draft_compare(self.path)
            return
        if parsed.path.startswith("/api/v1/draft/") and parsed.path.endswith("/history"):
            self._handle_draft_history(parsed.path)
            return
        if parsed.path == "/api/v1/process/drafts":
            qs = parse_qs(parsed.query)
            status = (qs.get("status", [""])[0] or "").strip()
            limit = _safe_int((qs.get("limit", ["50"])[0] or "50"), 50)
            items = runtime_store.list_process_drafts(status=status, limit=limit)
            self._send_json({"status": "ok", "items": items})
            return
        if parsed.path == "/api/v1/workflow/status":
            qs = parse_qs(parsed.query)
            workflow_id = (qs.get("workflow_id", [""])[0] or "").strip()
            if not workflow_id:
                self._send_json({"status": "error", "error": "workflow_id 不能为空"}, status=400)
                return
            data = workflow_runs.get(workflow_id)
            if not data:
                self._send_json({"status": "error", "error": "workflow_id 不存在", "workflow_id": workflow_id}, status=404)
                return
            self._send_json(data)
            return
        if parsed.path == "/api/v1/task/status":
            qs = parse_qs(parsed.query)
            task_run_id = (qs.get("task_run_id", [""])[0] or "").strip()
            if not task_run_id:
                self._send_json({"status": "error", "error": "task_run_id 不能为空"}, status=400)
                return
            task_data = runtime_store.get_task_run(task_run_id)
            if not task_data:
                self._send_json({"status": "error", "error": "task_run_id 不存在", "task_run_id": task_run_id}, status=404)
                return
            self._send_json({"status": "ok", "task_run": task_data})
            return
        # Phase 2: Task execution trace endpoint
        if parsed.path.startswith("/api/v1/task/") and "/trace" in parsed.path:
            parts = parsed.path.split("/")
            if len(parts) >= 4 and parts[-1] == "trace":
                task_run_id = parts[3]
                steps = runtime_store.list_step_runs(task_run_id) if hasattr(runtime_store, 'list_step_runs') else []
                self._send_json({"status": "ok", "task_run_id": task_run_id, "steps": steps})
                return
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/v1/agent/execute":
            self._handle_agent_execute()
            return
        if parsed.path == "/api/v1/process/definitions":
            self._handle_create_process_definition()
            return
        if parsed.path == "/api/v1/process/versions":
            self._handle_create_process_version()
            return
        if parsed.path == "/api/v1/process/expert/chat":
            self._handle_process_expert_chat()
            return
        if parsed.path == "/api/v1/workflow/start":
            self._handle_workflow_start()
            return
        if parsed.path == "/api/v1/router/decision":
            self._handle_router_decision()
            return
        # Phase 1: Confirmation and schema validation endpoints
        if parsed.path == "/api/v1/confirmation/respond":
            self._handle_confirmation_respond()
            return
        if parsed.path == "/api/v1/confirmation/batch":
            self._handle_confirmation_batch()
            return
        if parsed.path == "/api/v1/confirmation/cleanup-expired":
            self._handle_confirmation_cleanup_expired()
            return
        if parsed.path == "/api/v1/schema/validate":
            self._handle_schema_validate()
            return
        if parsed.path.startswith("/api/v1/draft/") and parsed.path.endswith("/restore"):
            self._handle_draft_restore(parsed.path)
            return
        self.send_error(404)

    def _handle_create_process_definition(self) -> None:
        body = self._read_json_body()
        code = str(body.get("code") or "").strip()
        name = str(body.get("name") or "").strip()
        domain = str(body.get("domain") or "").strip()
        owner_agent = str(body.get("owner_agent") or "process_expert")
        if not code or not name or not domain:
            self._send_json({"status": "error", "error": "code/name/domain 不能为空"}, status=400)
            return
        try:
            item = runtime_store.create_process_definition(code=code, name=name, domain=domain, owner_agent=owner_agent)
            server_state["requests_total"] = int(server_state.get("requests_total", 0)) + 1
            self._send_json({"status": "ok", "process_definition": item})
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=400)

    def _handle_create_process_version(self) -> None:
        body = self._read_json_body()
        process_definition_id = str(body.get("process_definition_id") or "").strip()
        version = str(body.get("version") or "").strip()
        goal = str(body.get("goal") or "").strip()
        steps = body.get("steps") or []
        publish = bool(body.get("publish"))
        reason = str(body.get("reason") or "").strip()
        tool_bundle_version = str(body.get("tool_bundle_version") or "bundle-default@1.0.0").strip()
        engine_version = str(body.get("engine_version") or "factory-engine@1.0.0").strip()
        engine_compatibility = body.get("engine_compatibility")
        if not isinstance(engine_compatibility, dict):
            engine_compatibility = {"min_engine_version": "1.0.0", "max_engine_version": "1.x"}
        if not process_definition_id or not version:
            self._send_json({"status": "error", "error": "process_definition_id/version 不能为空"}, status=400)
            return
        try:
            event_params = {
                "process_definition_id": process_definition_id,
                "version": version,
                "goal": goal,
                "publish": publish,
                "reason": reason,
                "tool_bundle_version": tool_bundle_version,
                "engine_version": engine_version,
                "engine_compatibility": engine_compatibility,
            }
            pre_state = _capture_iteration_pre_state("create_version", event_params)
            if pre_state:
                event_params.update(pre_state)
            item = runtime_store.create_process_version(
                process_definition_id=process_definition_id,
                version=version,
                goal=goal,
                steps=steps,
                publish=publish,
                created_by="process_expert",
                tool_bundle_version=tool_bundle_version,
                engine_version=engine_version,
                engine_compatibility=engine_compatibility,
            )
            _record_iteration_event_if_needed(
                intent="create_version",
                params=event_params,
                tool_result={"status": "ok", "intent": "create_version", "process_version": item},
            )
            server_state["requests_total"] = int(server_state.get("requests_total", 0)) + 1
            self._send_json({"status": "ok", "process_version": item})
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=400)

    def _handle_process_expert_chat(self) -> None:
        body = self._read_json_body()
        if "dry_run" in body:
            self._send_json({"status": "error", "error": "dry_run 已禁用：工艺设计必须调用大模型"}, status=400)
            return
        action = str(body.get("action") or "design").strip()
        if action == "chat":
            message = str(body.get("message") or "").strip()
            if not message:
                self._send_json({"status": "error", "error": "message 不能为空"}, status=400)
                return
            session_id = str(body.get("session_id") or f"chat_{uuid.uuid4().hex[:10]}")
            try:
                data = _run_process_expert_chat_turn(session_id=session_id, user_message=message)
                self._send_json(data)
            except Exception as exc:
                self._send_json({"status": "error", "error": str(exc)}, status=500)
            return

        if action == "design":
            requirement = str(body.get("requirement") or "").strip()
            if not requirement:
                self._send_json({"status": "error", "error": "requirement 不能为空"}, status=400)
                return
            data = _create_design_draft(
                requirement=requirement,
                process_code=str(body.get("process_code") or ""),
                process_name=str(body.get("process_name") or ""),
                domain=str(body.get("domain") or "address_governance"),
                goal=str(body.get("goal") or ""),
            )
            self._send_json(data)
            return

        if action == "publish_draft":
            draft_id = str(body.get("draft_id") or "").strip()
            reason = str(body.get("reason") or "").strip()
            operator = str(body.get("operator") or "").strip()
            source = str(body.get("source") or "process_console").strip()
            t0 = time.time()
            event_params = {"draft_id": draft_id, "reason": reason, "operator": operator, "source": source}
            pre_state = _capture_iteration_pre_state("publish_draft", event_params)
            if pre_state:
                event_params.update(pre_state)
            data = _publish_draft(draft_id, reason=reason, operator=operator, source=source)
            if isinstance(data, dict):
                publish_audit = dict(data.get("publish_audit") or {})
                publish_audit["latency_ms"] = int((time.time() - t0) * 1000)
                data["publish_audit"] = publish_audit
            _record_iteration_event_if_needed(
                intent="publish_draft",
                params=event_params,
                tool_result=data if isinstance(data, dict) else {},
            )
            if isinstance(data, dict):
                _log_operation_audit(
                    operation_type="publish_draft",
                    operation_status=str(data.get("status") or "unknown").lower(),
                    actor=operator or "unknown",
                    source=source or "process_console",
                    confirmation_id=str((data.get("publish_audit") or {}).get("confirmation_id") or ""),
                    confirmer_user_id=str((data.get("publish_audit") or {}).get("confirmer_user_id") or ""),
                    draft_id=draft_id,
                    process_definition_id=str(data.get("process_definition_id") or ""),
                    process_version_id=str(data.get("process_version_id") or ""),
                    error_code=str(data.get("error") or ""),
                    detail={"path": "process_expert_chat_publish_action", "reason": reason},
                )
            if data.get("status") != "ok":
                self._send_json(data, status=404)
                return
            self._send_json(data)
            return

        if action == "query":
            question = str(body.get("question") or "").strip()
            q = question.lower()

            if ("查询工艺" in question) or ("query process" in q):
                code = _extract_field(
                    question,
                    [
                        r"code\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"编码\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                ).upper()
                name = _extract_field(
                    question,
                    [
                        r"name\s*[:=]\s*([^\s,，]+)",
                        r"名称\s*[：:]\s*([^\n,，]+)",
                    ],
                )
                items = runtime_store.list_process_definitions()
                if code:
                    items = [x for x in items if str(x.get("code") or "").upper() == code]
                if name:
                    items = [x for x in items if name in str(x.get("name") or "")]
                self._send_json({"status": "ok", "intent": "query_process", "items": items})
                return

            if ("查询版本" in question) or ("query version" in q):
                process_definition_id = _extract_field(
                    question,
                    [
                        r"process_definition_id\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"工艺ID\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                )
                code = _extract_field(
                    question,
                    [
                        r"code\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"编码\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                ).upper()
                if not process_definition_id and code:
                    defs = runtime_store.list_process_definitions()
                    hit = next((x for x in defs if str(x.get("code") or "").upper() == code), None)
                    if hit:
                        process_definition_id = str(hit.get("id") or "")
                if not process_definition_id:
                    self._send_json({"status": "ok", "intent": "query_version", "items": []})
                    return
                self._send_json(
                    {
                        "status": "ok",
                        "intent": "query_version",
                        "process_definition_id": process_definition_id,
                        "items": runtime_store.list_process_versions(process_definition_id),
                    }
                )
                return

            if ("修改工艺" in question) or ("更新工艺" in question) or ("modify process" in q):
                process_definition_id = _extract_field(
                    question,
                    [
                        r"process_definition_id\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"工艺ID\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                )
                code = _extract_field(
                    question,
                    [
                        r"code\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"编码\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                ).upper()
                change_req = _extract_field(
                    question,
                    [
                        r"变更\s*[:=]\s*(.+)",
                        r"changes?\s*[:=]\s*(.+)",
                    ],
                ) or "补充工艺规则优化"

                defs = runtime_store.list_process_definitions()
                target = None
                if process_definition_id:
                    target = next((x for x in defs if x.get("id") == process_definition_id), None)
                if not target and code:
                    target = next((x for x in defs if str(x.get("code") or "").upper() == code), None)
                if not target:
                    self._send_json({"status": "error", "error": "未找到待修改工艺，请提供 code 或 process_definition_id"}, status=404)
                    return

                requirement = f"请在已有工艺 {target.get('code')} 基础上完成如下变更：{change_req}"
                plan = {
                    "auto_execute": True,
                    "max_duration": 1200,
                    "quality_threshold": 0.9,
                    "priority": 1,
                    "addresses": [],
                }
                llm_answer = ""
                try:
                    cfg = load_config(str(server_state.get("config_path") or "config/llm_api.json"))
                    sys_prompt = "你是工艺专家Agent，请基于变更需求输出工艺升级建议，并尽量给出JSON代码块。"
                    llm = run_requirement_query(requirement=requirement, config=cfg, system_prompt_override=sys_prompt)
                    llm_answer = llm.get("answer", "")
                    parsed = parse_plan_from_answer(llm_answer)
                    if parsed:
                        plan = parsed
                except Exception:
                    llm_answer = "模型调用失败，已使用默认升级草案。"

                draft_id = f"draft_{uuid.uuid4().hex[:10]}"
                process_doc = "\n".join(
                    [
                        f"# 工艺流程文档（升级草案）：{target.get('name')}",
                        "",
                        f"- process_code: `{target.get('code')}`",
                        f"- process_definition_id: `{target.get('id')}`",
                        f"- change_request: {change_req}",
                        f"- auto_execute: {plan.get('auto_execute')}",
                        f"- quality_threshold: {plan.get('quality_threshold')}",
                        "## 升级步骤",
                        "1. 保留既有输入与输出契约",
                        "2. 增加核实策略与失败分类规则",
                        "3. 发布新版本并灰度验证",
                    ]
                )
                draft = {
                    "draft_id": draft_id,
                    "base_process_definition_id": target.get("id"),
                    "requirement": requirement,
                    "process_code": target.get("code"),
                    "process_name": target.get("name"),
                    "domain": target.get("domain"),
                    "goal": change_req,
                    "plan": plan,
                    "process_doc_markdown": process_doc,
                    "created_at": _now_iso(),
                }
                process_design_drafts[draft_id] = draft
                self._send_json({"status": "ok", "intent": "modify_process", **draft, "llm_answer": llm_answer})
                return

            if ("创建工艺" in question) or ("create process" in q):
                code = _extract_field(
                    question,
                    [
                        r"code\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"编码\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                ).upper()
                name = _extract_field(
                    question,
                    [
                        r"name\s*[:=]\s*([^\s,，]+)",
                        r"名称\s*[：:]\s*([^\n,，]+)",
                    ],
                )
                domain = _extract_field(
                    question,
                    [
                        r"domain\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"领域\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                ) or "address_governance"
                if not code:
                    self._send_json(
                        {"status": "error", "error": "缺少工艺编码，请在问题中提供 code=<工艺编码>"},
                        status=400,
                    )
                    return
                if not name:
                    name = f"{code} 工艺"
                item = runtime_store.create_process_definition(
                    code=code,
                    name=name,
                    domain=domain,
                    owner_agent="process_expert",
                )
                self._send_json({"status": "ok", "intent": "create_process", "process_definition": item})
                return

            if ("创建版本" in question) or ("create version" in q):
                process_definition_id = _extract_field(
                    question,
                    [
                        r"process_definition_id\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"工艺ID\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                )
                version = _extract_field(
                    question,
                    [
                        r"version\s*[:=]\s*([0-9]+\.[0-9]+\.[0-9]+)",
                        r"版本\s*[：:]\s*([0-9]+\.[0-9]+\.[0-9]+)",
                    ],
                )
                goal = _extract_field(
                    question,
                    [
                        r"goal\s*[:=]\s*([^\n]+)",
                        r"目标\s*[：:]\s*([^\n]+)",
                    ],
                ) or "对话式创建版本"
                publish = ("发布" in question) or ("publish" in q)
                if not process_definition_id or not version:
                    self._send_json(
                        {
                            "status": "error",
                            "error": "缺少 process_definition_id 或 version，请在问题中提供 process_definition_id=<id> version=<x.y.z>",
                        },
                        status=400,
                    )
                    return
                steps = [
                    {"step_code": "INPUT_PREP", "name": "输入准备", "tool_name": "input_prep_tool", "process_type": "自动化"},
                    {"step_code": "PROCESS", "name": "工艺处理", "tool_name": "process_tool", "process_type": "自动化"},
                    {"step_code": "OUTPUT_JSON", "name": "输出入库", "tool_name": "output_json_tool", "process_type": "自动化"},
                ]
                item = runtime_store.create_process_version(
                    process_definition_id=process_definition_id,
                    version=version,
                    goal=goal,
                    steps=steps,
                    publish=publish,
                    created_by="process_expert",
                )
                self._send_json({"status": "ok", "intent": "create_version", "process_version": item})
                return

            if ("查询工艺任务" in question) or ("process tasks" in q):
                process_definition_id = _extract_field(
                    question,
                    [
                        r"process_definition_id\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"工艺ID\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                )
                if not process_definition_id:
                    self._send_json({"status": "error", "error": "缺少 process_definition_id"}, status=400)
                    return
                self._send_json(
                    {
                        "status": "ok",
                        "intent": "query_process_tasks",
                        "items": runtime_store.list_tasks_by_process_definition(process_definition_id),
                    }
                )
                return

            if ("查询任务输入输出" in question) or ("task io" in q):
                task_run_id = _extract_field(
                    question,
                    [
                        r"task_run_id\s*[:=]\s*([A-Za-z0-9_]+)",
                        r"任务ID\s*[：:]\s*([A-Za-z0-9_]+)",
                    ],
                )
                if not task_run_id:
                    self._send_json({"status": "error", "error": "缺少 task_run_id"}, status=400)
                    return
                item = runtime_store.get_task_run(task_run_id)
                if not item:
                    self._send_json({"status": "error", "error": "task_run_id 不存在"}, status=404)
                    return
                self._send_json({"status": "ok", "intent": "query_task_io", "task_run": item})
                return

            if ("版本" in question) or ("version" in question.lower()):
                defs = runtime_store.list_process_definitions()
                items = []
                for d in defs:
                    versions = runtime_store.list_process_versions(d["id"])
                    items.append({"process": d, "versions": versions})
                self._send_json({"status": "ok", "items": items})
                return
            self._send_json({"status": "ok", "items": runtime_store.list_process_definitions()})
            return

        self._send_json({"status": "error", "error": f"不支持 action: {action}"}, status=400)

    def _handle_agent_execute(self) -> None:
        body = self._read_json_body()
        agent_type = str(body.get("agent_type") or "").strip()
        request_id = str(body.get("request_id") or "")
        if not agent_type:
            decision = _route_request(body, body.get("task_spec") if isinstance(body.get("task_spec"), dict) else None)
            agent_type = str(decision.get("preferred_agent") or "").strip()
            if not agent_type:
                self._send_json({"status": "error", "error": "agent_type 不能为空", "request_id": request_id}, status=400)
                return
        fn = AGENT_HANDLERS.get(agent_type)
        if not fn:
            self._send_json(
                {
                    "status": "error",
                    "error": f"不支持的 agent_type: {agent_type}",
                    "request_id": request_id,
                    "allowed_agents": sorted(AGENT_HANDLERS.keys()),
                },
                status=400,
            )
            return

        t0 = time.time()
        try:
            result = fn(body)
            server_state["requests_total"] = int(server_state.get("requests_total", 0)) + 1
            if result.get("status") != "ok":
                self._send_json(result, status=400)
                return
            result["latency_ms"] = int((time.time() - t0) * 1000)
            if request_id:
                result["request_id"] = request_id
            self._send_json(result)
        except Exception as exc:
            self._send_json(
                {
                    "status": "error",
                    "error": str(exc),
                    "request_id": request_id,
                    "agent_type": agent_type,
                },
                status=500,
            )

    def _handle_router_decision(self) -> None:
        body = self._read_json_body()
        task_spec = body.get("task_spec") if isinstance(body.get("task_spec"), dict) else None
        decision = _route_request(body, task_spec)
        self._send_json({"status": "ok", "router_decision": decision})

    def _handle_workflow_start(self) -> None:
        body = self._read_json_body()
        request_id = str(body.get("request_id") or "")
        t0 = time.time()
        try:
            result = _run_orchestrated_workflow(body)
            server_state["requests_total"] = int(server_state.get("requests_total", 0)) + 1
            result["latency_ms"] = int((time.time() - t0) * 1000)
            if request_id:
                result["request_id"] = request_id
            self._send_json(result)
        except Exception as exc:
            self._send_json(
                {
                    "status": "error",
                    "error": str(exc),
                    "request_id": request_id,
                    "api": "/api/v1/workflow/start",
                },
                status=500,
            )

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    # Phase 1: Confirmation handler
    def _handle_confirmation_respond(self) -> None:
        body = self._read_json_body()
        confirmation_id = str(body.get("confirmation_id") or "").strip()
        response = str(body.get("response") or "").strip().lower()
        confirmer_user_id = str(body.get("confirmer_user_id") or "user").strip()

        if not confirmation_id:
            self._send_json({"status": "error", "error": "confirmation_id 不能为空"}, status=400)
            return

        if response not in {"confirm", "reject"}:
            self._send_json({"status": "error", "error": "response 必须是 confirm 或 reject"}, status=400)
            return

        try:
            confirmation = runtime_store.get_confirmation_record(confirmation_id)
            if not confirmation:
                self._send_json({"status": "error", "error": "确认记录不存在"}, status=404)
                return

            if response == "confirm":
                _, _, confirm_svc = _get_control_plane_services()
                result = confirm_svc.respond_single(
                    confirmation_id=confirmation_id,
                    response="confirm",
                    confirmer_user_id=confirmer_user_id,
                )
                self._send_json({
                    "status": result.get("status"),
                    "message": result.get("message"),
                    "confirmation_id": confirmation_id,
                    "tool_result": result.get("tool_result"),
                })
            else:
                _, _, confirm_svc = _get_control_plane_services()
                result = confirm_svc.respond_single(
                    confirmation_id=confirmation_id,
                    response="reject",
                    confirmer_user_id=confirmer_user_id,
                )
                self._send_json({
                    "status": result.get("status"),
                    "message": result.get("message"),
                    "confirmation_id": confirmation_id,
                })
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    def _handle_confirmation_batch(self) -> None:
        body = self._read_json_body()
        confirmation_ids = body.get("confirmation_ids") or []
        response = str(body.get("response") or "").strip().lower()
        confirmer_user_id = str(body.get("confirmer_user_id") or "user").strip()
        if not isinstance(confirmation_ids, list) or not confirmation_ids:
            self._send_json({"status": "error", "error": "confirmation_ids 不能为空"}, status=400)
            return
        if response not in {"confirm", "reject"}:
            self._send_json({"status": "error", "error": "response 必须是 confirm 或 reject"}, status=400)
            return

        _, _, confirm_svc = _get_control_plane_services()
        result = confirm_svc.respond_batch(
            confirmation_ids=confirmation_ids,
            response=response,
            confirmer_user_id=confirmer_user_id,
        )
        self._send_json(result)

    def _handle_confirmation_cleanup_expired(self) -> None:
        try:
            _, _, confirm_svc = _get_control_plane_services()
            self._send_json(confirm_svc.cleanup_expired())
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    # Phase 1: Schema validation handler
    def _handle_schema_validate(self) -> None:
        body = self._read_json_body()
        intent = str(body.get("intent") or "").strip()
        params = body.get("params", {})

        if not intent:
            self._send_json({"status": "error", "error": "intent 不能为空"}, status=400)
            return

        try:
            validation: ValidationResult = schema_validator.validate(intent, params)

            # Log parsing event
            runtime_store.log_parsing_event(
                session_id=body.get("session_id", ""),
                raw_llm_response="",
                parsed_json=json.dumps(params, ensure_ascii=False),
                validation_status="valid" if validation.is_valid else "invalid",
                validation_errors=json.dumps(validation.errors, ensure_ascii=False),
            )

            self._send_json({
                "status": "ok" if validation.is_valid else "validation_error",
                "valid": validation.is_valid,
                "intent": validation.intent,
                "errors": validation.errors,
                "sanitized_params": validation.sanitized_params,
            })
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    # Phase 2: Draft comparison handlers
    def _handle_draft_compare(self, path: str) -> None:
        """Handle draft version comparison (GET)."""
        qs = parse_qs(urlparse(path).query)
        raw_path = urlparse(path).path
        parts = raw_path.split("/")
        draft_id = parts[4] if len(parts) >= 6 else ""
        v1 = int((qs.get("v1", ["1"])[0] or "1"))
        v2 = int((qs.get("v2", ["1"])[0] or "1"))

        if not draft_id:
            self._send_json({"status": "error", "error": "draft_id 不能为空"}, status=400)
            return

        try:
            version1 = runtime_store.get_draft_version(draft_id, v1)
            version2 = runtime_store.get_draft_version(draft_id, v2)

            # Compute diff
            diff = {}
            if version1 and version2:
                for field in ["process_code", "process_name", "goal", "domain", "plan_json", "process_doc_markdown"]:
                    val1 = version1.get(field)
                    val2 = version2.get(field)
                    if val1 != val2:
                        diff[field] = {"before": val1, "after": val2, "type": "modified"}

            self._send_json({
                "status": "ok",
                "draft_id": draft_id,
                "version_a": v1,
                "version_b": v2,
                "field_diffs": diff,
            })
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    def _handle_draft_restore(self, path: str) -> None:
        """Handle draft version restoration (POST)."""
        body = self._read_json_body()
        raw_path = urlparse(path).path
        parts = raw_path.split("/")
        draft_id = parts[4] if len(parts) >= 6 else ""
        version_sequence = int(body.get("version_sequence", 1))

        if not draft_id:
            self._send_json({"status": "error", "error": "draft_id 不能为空"}, status=400)
            return

        try:
            old_version = runtime_store.get_draft_version(draft_id, version_sequence)
            if not old_version:
                self._send_json({"status": "error", "error": f"版本 {version_sequence} 不存在"}, status=404)
                return

            # Restore by updating the draft with old version content
            runtime_store.upsert_process_draft(
                draft_id=draft_id,
                session_id=old_version.get("session_id", ""),
                process_code=old_version.get("process_code"),
                process_name=old_version.get("process_name"),
                domain=old_version.get("domain"),
                goal=old_version.get("goal"),
                plan_json=old_version.get("plan_json"),
                process_doc_markdown=old_version.get("process_doc_markdown"),
                status="editable",
            )

            self._send_json({
                "status": "ok",
                "message": f"已恢复到版本 {version_sequence}",
                "draft_id": draft_id,
            })
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    def _handle_draft_history(self, path: str) -> None:
        """Handle draft history retrieval (GET)."""
        raw_path = urlparse(path).path
        parts = raw_path.split("/")
        draft_id = parts[4] if len(parts) >= 6 else ""

        if not draft_id:
            self._send_json({"status": "error", "error": "draft_id 不能为空"}, status=400)
            return

        try:
            history = runtime_store.list_draft_version_history(draft_id)
            self._send_json({
                "status": "ok",
                "draft_id": draft_id,
                "versions": history,
            })
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    def _handle_task_trace(self, path: str) -> None:
        """Handle task execution trace retrieval (GET)."""
        parts = path.split("/")
        if len(parts) < 4:
            self._send_json({"status": "error", "error": "Invalid path"}, status=400)
            return

        task_run_id = parts[3]

        try:
            steps = runtime_store.list_step_runs(task_run_id) if hasattr(runtime_store, 'list_step_runs') else []
            trace_steps = []
            for step in steps:
                duration_ms = None
                if step.get("started_at") and step.get("ended_at"):
                    try:
                        from datetime import datetime
                        start = datetime.fromisoformat(step["started_at"])
                        end = datetime.fromisoformat(step["ended_at"])
                        duration_ms = int((end - start).total_seconds() * 1000)
                    except Exception:
                        pass

                trace_steps.append({
                    "step_index": step.get("step_index", 0),
                    "step_code": step.get("step_code", ""),
                    "round_number": step.get("round", 1),
                    "status": step.get("status", ""),
                    "started_at": step.get("started_at"),
                    "ended_at": step.get("ended_at"),
                    "duration_ms": duration_ms,
                    "error_code": step.get("error_code"),
                    "error_detail": step.get("error_detail"),
                    "summary": step.get("display_summary", f"{step.get('step_code')} 步骤"),
                })

            self._send_json({
                "status": "ok",
                "task_run_id": task_run_id,
                "steps": trace_steps,
            })
        except Exception as exc:
            self._send_json({"status": "error", "error": str(exc)}, status=500)

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt: str, *args):
        pass


def start_agent_server(
    port: int = 8081,
    config_path: str = "config/llm_api.json",
    runtime_db_path: str = "database/agent_runtime.db",
    runtime_store_dir: str = "runtime_store",
):
    global runtime_store, process_db_api
    runtime_store = AgentRuntimeStore(db_path=runtime_db_path, base_dir=runtime_store_dir)
    process_db_api = ProcessDBApi(runtime_store=runtime_store, process_design_drafts=process_design_drafts)
    server_state["status"] = "running"
    server_state["started_at"] = _now_iso()
    server_state["config_path"] = config_path
    server_state["requests_total"] = 0

    # Phase 3: Initialize ToolRegistry before starting HTTP server
    logger.info("[INIT] Initializing ToolRegistry...")
    init_tool_registry()

    server = HTTPServer(("", port), AgentServerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Agent Server（统一 Agent 入口）")
    parser.add_argument("--port", type=int, default=8081, help="服务端口")
    parser.add_argument("--config", default="config/llm_api.json", help="LLM 配置文件路径")
    parser.add_argument("--runtime-db", default="database/agent_runtime.db", help="运行时SQLite")
    parser.add_argument("--runtime-store", default="runtime_store", help="输入原始文件本地目录")
    args = parser.parse_args(argv)

    server = start_agent_server(
        port=args.port,
        config_path=args.config,
        runtime_db_path=args.runtime_db,
        runtime_store_dir=args.runtime_store,
    )
    print("=" * 72)
    print("Agent Server 已启动")
    print(f"地址: http://127.0.0.1:{args.port}")
    print(f"Health: http://127.0.0.1:{args.port}/healthz")
    print(f"配置: {args.config}")
    print("按 Ctrl+C 停止")
    print("=" * 72)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
