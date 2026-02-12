import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.runtime.orchestrator import Orchestrator
from src.runtime.errors import InvalidTransitionError


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.db = PROJECT_ROOT / "database" / "agent_runtime_test.db"
        if self.db.exists():
            self.db.unlink()
        self.o = Orchestrator(
            state_store=None,
            evidence_store=None,
        )
        # Override stores to use isolated test db
        from src.runtime.state_store import SQLiteStateStore
        from src.runtime.evidence_store import SQLiteEvidenceStore

        self.o.state_store = SQLiteStateStore(str(self.db))
        self.o.evidence_store = SQLiteEvidenceStore(str(self.db))

    def tearDown(self):
        if self.db.exists():
            self.db.unlink()

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
