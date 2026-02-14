"""Agent Server: 统一 Agent 入口、路由与编排主控。"""

from __future__ import annotations

import argparse
import json
import logging
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
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

# Phase 3: ToolRegistry integration imports
from tools.registry_manager import (
    initialize_registry,
    execute_tool as execute_tool_via_registry,
    list_registered_intents,
    ToolRegistryManager,
)
from tools.agent_framework import SessionState, ChatState


server_state: Dict[str, Any] = {
    "status": "starting",
    "started_at": None,
    "config_path": "config/llm_api.json",
    "requests_total": 0,
}
workflow_runs: Dict[str, Dict[str, Any]] = {}

planner_adapter = PlannerAdapter()
executor_adapter = ExecutorAdapter()
evaluator_adapter = EvaluatorAdapter()
runtime_store = AgentRuntimeStore()
process_compiler = ProcessCompiler()
process_design_drafts: Dict[str, Dict[str, Any]] = {}
process_chat_sessions: Dict[str, List[Dict[str, str]]] = {}
process_chat_pending_ops: Dict[str, Dict[str, Any]] = {}
process_db_api = ProcessDBApi(runtime_store=runtime_store, process_design_drafts=process_design_drafts)
schema_validator = DialogueSchemaValidator()  # Phase 1: Parameter validation
WRITE_INTENTS = {"create_process", "create_version", "publish_draft"}

# Phase 3: ToolRegistry and SessionState initialization
registry_initialized = False
session_states: Dict[str, SessionState] = {}  # session_id -> SessionState
tool_registry = None

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


def _publish_draft(draft_id: str) -> Dict[str, Any]:
    draft = runtime_store.get_process_draft(draft_id)
    if draft:
        process_design_drafts[draft_id] = {
            "draft_id": draft.get("draft_id"),
            "requirement": draft.get("requirement"),
            "process_code": draft.get("process_code"),
            "process_name": draft.get("process_name"),
            "domain": draft.get("domain"),
            "goal": draft.get("goal"),
            "plan": draft.get("plan") or {},
            "process_doc_markdown": draft.get("process_doc_markdown") or "",
            "created_at": draft.get("created_at"),
        }
    data = process_db_api.publish_draft({"draft_id": draft_id})
    if "intent" in data:
        data = dict(data)
        data.pop("intent", None)
    if data.get("status") == "ok":
        runtime_store.mark_process_draft_published(draft_id)
    return data


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
        if confirmation_id:
            # Update confirmation record status
            runtime_store.update_confirmation_status(confirmation_id, "confirmed", "user")

        tool_result = _execute_process_expert_intent(
            pending["intent"],
            pending["params"],
            session_id=session_id  # NEW: pass session_id
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

    if intent in WRITE_INTENTS:
        execute = False

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
        if intent in WRITE_INTENTS and not execute:
            # Phase 1: Create structured confirmation record
            expires_at = (datetime.now() + timedelta(seconds=900)).isoformat()  # 15-minute expiry
            confirmation_id = runtime_store.create_confirmation_record(
                session_id=session_id,
                operation_type=intent,
                operation_params=params,
                draft_id=str((params or {}).get("draft_id") or ""),
                expires_at=expires_at,
            )

            tool_result = {
                "status": "pending_confirmation",
                "intent": intent,
                "confirmation_id": confirmation_id,
                "message": "已生成数据库与文件操作脚本，待你确认后执行。",
                "params": params,
            }
            process_chat_pending_ops[session_id] = {
                "intent": intent,
                "params": params,
                "operation_scripts": operation_scripts,
                "confirmation_id": confirmation_id,
            }
        else:
            tool_result = _execute_process_expert_intent(intent, params, session_id=session_id)
            update_session_from_tool_result(session_id, intent, tool_result)
            if intent in WRITE_INTENTS:
                process_chat_pending_ops.pop(session_id, None)
    assistant_message = str(parsed.get("assistant_reply") or "").strip()
    if not assistant_message:
        if tool_result.get("status") == "pending_confirmation":
            assistant_message = "我已整理操作方案和脚本，回复“确认执行”后我会写入数据库。"
        elif tool_result.get("status") == "ok":
            assistant_message = f"已完成操作：{intent}"
        else:
            assistant_message = f"执行失败：{tool_result.get('error', 'unknown')}"
    if intent in WRITE_INTENTS and tool_result.get("status") == "pending_confirmation":
        assistant_message = "写操作已进入确认门禁，请调用确认接口后执行。"
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
    workflow_id = str(payload.get("workflow_id") or f"wf_{uuid.uuid4().hex[:12]}")
    max_rounds = int(payload.get("max_rounds", 3) or 3)
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

    for round_index in range(1, max_rounds + 1):
        task_spec = json.loads(json.dumps(task_spec_base, ensure_ascii=False))
        task_spec["task_id"] = f"{task_spec_base['task_id']}_r{round_index}"
        if strategy_patch:
            task_spec.setdefault("context", {})
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
            "plan_id": plan.get("plan_id"),
            "execution_status": execution_result.get("status"),
            "eval_status": eval_report.get("status"),
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
        # Phase 2: Draft version history endpoint
        if parsed.path.startswith("/api/v1/draft/") and parsed.path.endswith("/history"):
            draft_id = parsed.path.split("/")[-2]
            if not draft_id:
                self._send_json({"status": "error", "error": "draft_id 不能为空"}, status=400)
                return
            history = runtime_store.list_draft_version_history(draft_id)
            self._send_json({"status": "ok", "draft_id": draft_id, "versions": history})
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
        # Phase 1: Confirmation and schema validation endpoints
        if parsed.path == "/api/v1/confirmation/respond":
            self._handle_confirmation_respond()
            return
        if parsed.path == "/api/v1/schema/validate":
            self._handle_schema_validate()
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
        if not process_definition_id or not version:
            self._send_json({"status": "error", "error": "process_definition_id/version 不能为空"}, status=400)
            return
        try:
            item = runtime_store.create_process_version(
                process_definition_id=process_definition_id,
                version=version,
                goal=goal,
                steps=steps,
                publish=publish,
                created_by="process_expert",
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
            data = _publish_draft(draft_id)
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
                # Execute the operation
                runtime_store.update_confirmation_status(confirmation_id, "confirmed", "user")
                tool_result = _execute_process_expert_intent(
                    confirmation["operation_type"], confirmation["operation_params"]
                )
                self._send_json({
                    "status": "ok",
                    "message": "操作已确认并执行",
                    "confirmation_id": confirmation_id,
                    "tool_result": tool_result,
                })
            else:
                # Reject the operation
                runtime_store.update_confirmation_status(confirmation_id, "rejected", "user")
                self._send_json({
                    "status": "ok",
                    "message": "操作已取消",
                    "confirmation_id": confirmation_id,
                })
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
        draft_id = path.split("/")[3] if len(path.split("/")) > 3 else ""
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
        draft_id = path.split("/")[3] if len(path.split("/")) > 3 else ""
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
        draft_id = path.split("/")[3] if len(path.split("/")) > 3 else ""

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
