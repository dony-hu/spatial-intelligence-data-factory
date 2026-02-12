from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .errors import InvalidTransitionError, NotFoundError
from .evidence_store import SQLiteEvidenceStore
from .state_store import SQLiteStateStore
from .policies import check_required_approvals


@dataclass
class TaskRuntimeState:
    task_id: str
    state: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approvals_required: List[str] = field(default_factory=list)
    approvals_granted: List[str] = field(default_factory=list)
    context: Dict = field(default_factory=dict)


class Orchestrator:
    """Minimal orchestrator with explicit state machine + evidence recording."""

    TRANSITIONS = {
        "SUBMITTED": {"PLANNED", "FAILED"},
        "PLANNED": {"APPROVAL_PENDING", "APPROVED", "FAILED"},
        "APPROVAL_PENDING": {"APPROVED", "FAILED"},
        "APPROVED": {"CHANGESET_READY", "FAILED"},
        "CHANGESET_READY": {"EXECUTING", "FAILED"},
        "EXECUTING": {"EVALUATING", "FAILED", "ROLLED_BACK"},
        "EVALUATING": {"COMPLETED", "FAILED", "NEEDS_HUMAN"},
        "NEEDS_HUMAN": {"APPROVED", "FAILED"},
        "COMPLETED": set(),
        "FAILED": set(),
        "ROLLED_BACK": set(),
    }

    def __init__(
        self,
        state_store: Optional[SQLiteStateStore] = None,
        evidence_store: Optional[SQLiteEvidenceStore] = None,
    ):
        self.state_store = state_store or SQLiteStateStore()
        self.evidence_store = evidence_store or SQLiteEvidenceStore()

    def submit(self, task_id: str, context: Optional[Dict] = None, approvals_required: Optional[List[str]] = None) -> Dict:
        payload = TaskRuntimeState(
            task_id=task_id,
            state="SUBMITTED",
            context=context or {},
            approvals_required=approvals_required or [],
        )
        self.state_store.upsert(task_id, payload.state, payload.__dict__)
        self.evidence_store.append(
            task_id,
            actor="orchestrator",
            action="state_transition",
            artifact_ref=f"{task_id}#INIT->SUBMITTED",
            result="success",
            metadata={"to": "SUBMITTED"},
        )
        return payload.__dict__

    def get(self, task_id: str) -> Dict:
        current = self.state_store.get(task_id)
        if not current:
            raise NotFoundError(f"task not found: {task_id}")
        return current

    def transition(self, task_id: str, to_state: str, actor: str = "orchestrator", metadata: Optional[Dict] = None) -> Dict:
        current = self.get(task_id)
        from_state = current["state"]
        allowed = self.TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidTransitionError(f"invalid transition: {from_state} -> {to_state}")

        payload = current["payload"]
        payload["state"] = to_state
        self.state_store.upsert(task_id, to_state, payload)
        self.evidence_store.append(
            task_id,
            actor=actor,
            action="state_transition",
            artifact_ref=f"{task_id}#{from_state}->{to_state}",
            result="success",
            metadata=metadata or {},
        )
        return self.get(task_id)

    def grant_approval(self, task_id: str, approval_type: str, actor: str = "human_gate") -> Dict:
        current = self.get(task_id)
        payload = current["payload"]
        granted = payload.get("approvals_granted", [])
        if approval_type not in granted:
            granted.append(approval_type)
        payload["approvals_granted"] = granted

        self.state_store.upsert(task_id, current["state"], payload)
        self.evidence_store.append(
            task_id,
            actor=actor,
            action="approval_granted",
            artifact_ref=f"{task_id}#approval:{approval_type}",
            result="success",
        )
        return self.get(task_id)

    def check_approvals(self, task_id: str) -> Dict:
        current = self.get(task_id)
        payload = current["payload"]
        result = check_required_approvals(
            payload.get("approvals_required", []),
            payload.get("approvals_granted", []),
        )
        self.evidence_store.append(
            task_id,
            actor="orchestrator",
            action="approval_gate_check",
            artifact_ref=f"{task_id}#approval-check",
            result="pass" if result["pass"] else "fail",
            metadata=result,
        )
        return result

    def evidence(self, task_id: str) -> List[Dict]:
        return self.evidence_store.list_by_task(task_id)

    def record_event(
        self,
        task_id: str,
        action: str,
        artifact_ref: str,
        result: str,
        actor: str = "orchestrator",
        metadata: Optional[Dict] = None,
    ) -> None:
        self.evidence_store.append(
            task_id=task_id,
            actor=actor,
            action=action,
            artifact_ref=artifact_ref,
            result=result,
            metadata=metadata or {},
        )
