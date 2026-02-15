from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now().isoformat()


class OperationAuditService:
    """Application-layer wrapper for operation audit logging/query."""

    def __init__(self, runtime_store):
        self.runtime_store = runtime_store

    def log(self, **kwargs) -> None:
        try:
            self.runtime_store.log_operation_audit(**kwargs)
        except Exception:
            # Keep audit non-blocking for control flow.
            return


class PublishService:
    """Application-layer wrapper for draft publishing + publish audit normalization."""

    def __init__(self, runtime_store, process_db_api, process_design_drafts: Dict[str, Dict[str, Any]]):
        self.runtime_store = runtime_store
        self.process_db_api = process_db_api
        self.process_design_drafts = process_design_drafts

    def publish_draft(self, draft_id: str, reason: str = "", operator: str = "", source: str = "") -> Dict[str, Any]:
        draft = self.runtime_store.get_process_draft(draft_id)
        if draft:
            self.process_design_drafts[draft_id] = {
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
        data = self.process_db_api.publish_draft({"draft_id": draft_id, "reason": reason})
        if "intent" in data:
            data = dict(data)
            data.pop("intent", None)
        if data.get("status") == "ok":
            self.runtime_store.mark_process_draft_published(draft_id)
        return self.attach_publish_audit(
            tool_result=data,
            draft_id=draft_id,
            reason=reason,
            operator=operator,
            source=source,
        )

    def attach_publish_audit(
        self,
        tool_result: Dict[str, Any],
        draft_id: str,
        reason: str = "",
        operator: str = "",
        source: str = "",
        confirmation_id: str = "",
        confirmer_user_id: str = "",
        latency_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not isinstance(tool_result, dict):
            return {"status": "error", "error": "invalid tool_result"}
        if str(tool_result.get("status") or "") != "ok":
            return tool_result
        if str(tool_result.get("intent") or "") not in {"", "publish_draft"} and "process_version_id" not in tool_result:
            return tool_result
        audit = dict(tool_result.get("publish_audit") or {})
        audit["draft_id"] = draft_id or str(tool_result.get("draft_id") or "")
        audit["reason"] = reason or str(audit.get("reason") or "")
        audit["operator"] = operator or str(audit.get("operator") or "unknown")
        audit["source"] = source or str(audit.get("source") or "process_expert_chat")
        audit["published_at"] = str(audit.get("published_at") or _now_iso())
        if confirmation_id:
            audit["confirmation_id"] = confirmation_id
        if confirmer_user_id:
            audit["confirmer_user_id"] = confirmer_user_id
        if latency_ms is not None:
            audit["latency_ms"] = int(latency_ms)
        tool_result["publish_audit"] = audit
        return tool_result


class ConfirmationWorkflowService:
    """Application-layer confirmation orchestration for confirm/reject/batch/cleanup."""

    def __init__(
        self,
        runtime_store,
        publish_service: PublishService,
        audit_service: OperationAuditService,
        execute_intent_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        capture_pre_state_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        record_iteration_event_fn: Callable[[str, Dict[str, Any], Dict[str, Any]], Optional[str]],
    ):
        self.runtime_store = runtime_store
        self.publish_service = publish_service
        self.audit_service = audit_service
        self.execute_intent_fn = execute_intent_fn
        self.capture_pre_state_fn = capture_pre_state_fn
        self.record_iteration_event_fn = record_iteration_event_fn

    def execute_confirmed(
        self,
        confirmation: Dict[str, Any],
        confirmation_id: str,
        confirmer_user_id: str,
        source: str = "confirmation_endpoint",
        actor: str = "",
        execute_intent_fn: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        started = datetime.now()
        self.runtime_store.update_confirmation_status(confirmation_id, "confirmed", confirmer_user_id)
        self.audit_service.log(
            operation_type=str(confirmation.get("operation_type") or ""),
            operation_status="confirmed",
            actor=actor or confirmer_user_id,
            source=source,
            confirmation_id=confirmation_id,
            confirmer_user_id=confirmer_user_id,
            session_id=str(confirmation.get("session_id") or ""),
            draft_id=str(confirmation.get("draft_id") or ""),
            detail={"path": "confirmation_execute_confirm"},
        )

        operation_type = str(confirmation.get("operation_type") or "")
        operation_params = dict(confirmation.get("operation_params") or {})
        event_params = dict(operation_params)
        pre_state = self.capture_pre_state_fn(operation_type, event_params)
        if isinstance(pre_state, dict) and pre_state:
            event_params.update(pre_state)

        intent_fn = execute_intent_fn or self.execute_intent_fn
        tool_result = intent_fn(operation_type, operation_params)
        if operation_type == "publish_draft" and isinstance(tool_result, dict):
            latency_ms = int((datetime.now() - started).total_seconds() * 1000)
            tool_result = self.publish_service.attach_publish_audit(
                tool_result=tool_result,
                draft_id=str(operation_params.get("draft_id") or ""),
                reason=str(operation_params.get("reason") or ""),
                operator=actor or "confirmation_api",
                source=source,
                confirmation_id=confirmation_id,
                confirmer_user_id=confirmer_user_id,
                latency_ms=latency_ms,
            )

        self.record_iteration_event_fn(
            operation_type,
            event_params,
            tool_result if isinstance(tool_result, dict) else {},
        )
        if isinstance(tool_result, dict):
            self.audit_service.log(
                operation_type=operation_type,
                operation_status=str(tool_result.get("status") or "unknown").lower(),
                actor="system",
                source=source,
                confirmation_id=confirmation_id,
                confirmer_user_id=confirmer_user_id,
                session_id=str(confirmation.get("session_id") or ""),
                draft_id=str(operation_params.get("draft_id") or confirmation.get("draft_id") or ""),
                process_definition_id=str(tool_result.get("process_definition_id") or ""),
                process_version_id=str(tool_result.get("process_version_id") or ""),
                error_code=str(tool_result.get("error") or ""),
                detail={"path": "confirmation_execute_result"},
            )
        return tool_result

    def reject_confirmation(
        self, confirmation: Dict[str, Any], confirmation_id: str, confirmer_user_id: str, source: str = "confirmation_endpoint"
    ) -> None:
        self.runtime_store.update_confirmation_status(confirmation_id, "rejected", confirmer_user_id)
        self.audit_service.log(
            operation_type=str(confirmation.get("operation_type") or ""),
            operation_status="rejected",
            actor=confirmer_user_id,
            source=source,
            confirmation_id=confirmation_id,
            confirmer_user_id=confirmer_user_id,
            session_id=str(confirmation.get("session_id") or ""),
            draft_id=str(confirmation.get("draft_id") or ""),
            detail={"path": "confirmation_reject"},
        )

    def respond_single(self, confirmation_id: str, response: str, confirmer_user_id: str) -> Dict[str, Any]:
        confirmation = self.runtime_store.get_confirmation_record(confirmation_id)
        if not confirmation:
            return {"status": "error", "error": "确认记录不存在"}
        if response == "confirm":
            tool_result = self.execute_confirmed(
                confirmation=confirmation,
                confirmation_id=confirmation_id,
                confirmer_user_id=confirmer_user_id,
            )
            return {
                "status": "ok",
                "message": "操作已确认并执行",
                "confirmation_id": confirmation_id,
                "tool_result": tool_result,
            }
        self.reject_confirmation(confirmation=confirmation, confirmation_id=confirmation_id, confirmer_user_id=confirmer_user_id)
        return {"status": "ok", "message": "操作已取消", "confirmation_id": confirmation_id}

    def respond_batch(self, confirmation_ids: List[str], response: str, confirmer_user_id: str) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for raw_id in confirmation_ids:
            confirmation_id = str(raw_id or "").strip()
            if not confirmation_id:
                continue
            confirmation = self.runtime_store.get_confirmation_record(confirmation_id)
            if not confirmation:
                results.append({"confirmation_id": confirmation_id, "status": "error", "error": "确认记录不存在"})
                continue
            try:
                if response == "confirm":
                    tool_result = self.execute_confirmed(
                        confirmation=confirmation,
                        confirmation_id=confirmation_id,
                        confirmer_user_id=confirmer_user_id,
                        source="confirmation_batch",
                        actor=confirmer_user_id,
                    )
                    results.append({"confirmation_id": confirmation_id, "status": "ok", "tool_result": tool_result})
                else:
                    self.reject_confirmation(
                        confirmation=confirmation,
                        confirmation_id=confirmation_id,
                        confirmer_user_id=confirmer_user_id,
                        source="confirmation_batch",
                    )
                    results.append({"confirmation_id": confirmation_id, "status": "ok", "message": "操作已取消"})
            except Exception as exc:
                results.append({"confirmation_id": confirmation_id, "status": "error", "error": str(exc)})
        ok_count = len([x for x in results if x.get("status") == "ok"])
        return {
            "status": "ok",
            "response": response,
            "requested": len(confirmation_ids),
            "succeeded": ok_count,
            "failed": len(results) - ok_count,
            "items": results,
        }

    def cleanup_expired(self) -> Dict[str, Any]:
        affected = self.runtime_store.expire_pending_confirmations()
        self.audit_service.log(
            operation_type="confirmation_cleanup_expired",
            operation_status="ok",
            actor="system",
            source="maintenance_api",
            detail={"affected": affected},
        )
        return {"status": "ok", "affected": affected}

    def create_pending_confirmation(
        self,
        session_id: str,
        intent: str,
        params: Dict[str, Any],
        expires_in_sec: int = 900,
        source: str = "process_expert_chat",
    ) -> Dict[str, Any]:
        expires_at = (datetime.now().timestamp() + int(expires_in_sec))
        expires_at_iso = datetime.fromtimestamp(expires_at).isoformat()
        confirmation_id = self.runtime_store.create_confirmation_record(
            session_id=session_id,
            operation_type=intent,
            operation_params=params,
            draft_id=str((params or {}).get("draft_id") or ""),
            expires_at=expires_at_iso,
        )
        self.audit_service.log(
            operation_type=intent,
            operation_status="pending_confirmation",
            actor="system",
            source=source,
            confirmation_id=confirmation_id,
            session_id=session_id,
            draft_id=str((params or {}).get("draft_id") or ""),
            detail={"path": "confirmation_create_pending"},
        )
        return {
            "status": "pending_confirmation",
            "intent": intent,
            "confirmation_id": confirmation_id,
            "message": "已生成数据库与文件操作脚本，待你确认后执行。",
            "params": params,
            "expires_at": expires_at_iso,
        }
