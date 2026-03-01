import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.runtime.orchestrator import Orchestrator
from src.runtime.errors import InvalidTransitionError


class _MemoryStateStore:
    def __init__(self):
        self._store = {}

    def upsert(self, task_id, state, payload):
        self._store[task_id] = {
            "task_id": task_id,
            "state": state,
            "payload": payload,
            "updated_at": "now",
        }

    def get(self, task_id):
        return self._store.get(task_id)


class _MemoryEvidenceStore:
    def __init__(self):
        self._rows = []

    def append(self, task_id, actor, action, artifact_ref, result, metadata=None):
        self._rows.append(
            {
                "task_id": task_id,
                "actor": actor,
                "action": action,
                "artifact_ref": artifact_ref,
                "result": result,
                "metadata": metadata or {},
            }
        )

    def list_by_task(self, task_id):
        return [row for row in self._rows if row["task_id"] == task_id]


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.o = Orchestrator(
            state_store=_MemoryStateStore(),
            evidence_store=_MemoryEvidenceStore(),
        )

    def test_submit_and_transition(self):
        self.o.submit("task_ut_1", approvals_required=["SECURITY"])
        self.o.transition("task_ut_1", "PLANNED")
        self.o.transition("task_ut_1", "APPROVAL_PENDING")

        state = self.o.get("task_ut_1")
        self.assertEqual(state["state"], "APPROVAL_PENDING")

    def test_invalid_transition(self):
        self.o.submit("task_ut_2")
        with self.assertRaises(InvalidTransitionError):
            self.o.transition("task_ut_2", "EXECUTING")

    def test_approval_gate(self):
        self.o.submit("task_ut_3", approvals_required=["SECURITY", "METRIC_DEFINITION"])
        self.o.transition("task_ut_3", "PLANNED")
        self.o.transition("task_ut_3", "APPROVAL_PENDING")

        r1 = self.o.check_approvals("task_ut_3")
        self.assertFalse(r1["pass"])
        self.assertIn("SECURITY", r1["missing"])

        self.o.grant_approval("task_ut_3", "SECURITY")
        self.o.grant_approval("task_ut_3", "METRIC_DEFINITION")
        r2 = self.o.check_approvals("task_ut_3")
        self.assertTrue(r2["pass"])

    def test_evidence_written(self):
        self.o.submit("task_ut_4")
        self.o.transition("task_ut_4", "PLANNED")
        events = self.o.evidence("task_ut_4")
        self.assertGreaterEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
