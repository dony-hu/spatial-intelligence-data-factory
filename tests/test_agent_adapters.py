import json
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.planner_adapter import PlannerAdapter
from src.agents.executor_adapter import ExecutorAdapter
from src.agents.evaluator_adapter import EvaluatorAdapter


class AgentAdapterTests(unittest.TestCase):
    def setUp(self):
        task_path = PROJECT_ROOT / "schemas" / "agent" / "examples" / "task-spec.sample.json"
        self.task_spec = json.loads(task_path.read_text(encoding="utf-8"))

    def test_planner_outputs_contracts(self):
        p = PlannerAdapter()
        plan, pack = p.plan(self.task_spec)
        cs = p.build_changeset(self.task_spec, plan, pack)

        self.assertEqual(plan["task_id"], self.task_spec["task_id"])
        self.assertIn("items", pack)
        self.assertGreater(len(cs["operations"]), 0)

    def test_executor_requires_approvals(self):
        p = PlannerAdapter()
        plan, pack = p.plan(self.task_spec)
        cs = p.build_changeset(self.task_spec, plan, pack)
        e = ExecutorAdapter()

        r = e.execute(self.task_spec, cs, approvals=[])
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["stage"], "GATE_CHECK")
        self.assertEqual(r["details"]["checks"][0]["name"], "Approval Gate")

    def test_evaluator_returns_evalreport(self):
        ev = EvaluatorAdapter()
        report = ev.evaluate(
            self.task_spec,
            {"operations": [{"idempotency_key": "k1"}]},
            {"status": "PASS", "stage": "EXECUTION"},
        )
        self.assertIn(report["status"], ["PASS", "FAIL", "NEEDS_HUMAN"])
        self.assertEqual(report["task_id"], self.task_spec["task_id"])


if __name__ == "__main__":
    unittest.main()
