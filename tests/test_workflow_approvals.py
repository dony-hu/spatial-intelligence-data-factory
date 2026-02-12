import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.factory_workflow import FactoryWorkflow
from testdata.factory_demo_scenarios import get_all_scenarios


class WorkflowApprovalTests(unittest.TestCase):
    def test_auto_execute_blocked_without_approvals(self):
        wf = FactoryWorkflow(factory_name="test-factory")
        scenario = get_all_scenarios()["quick_test"]()
        wf.submit_product_requirement(scenario)
        result = wf.create_production_workflow(scenario, auto_execute=True)

        self.assertEqual(result["status"], "pending_approval")
        self.assertIn("approval_gates", result["stages"])
        self.assertGreater(len(result["stages"]["approval_gates"]["missing"]), 0)

    def test_auto_execute_runs_after_approvals(self):
        wf = FactoryWorkflow(factory_name="test-factory-approved")
        wf.approve_all_required_gates(approver="unit-test", note="test")

        scenario = get_all_scenarios()["quick_test"]()
        wf.submit_product_requirement(scenario)
        result = wf.create_production_workflow(scenario, auto_execute=True)

        self.assertEqual(result["status"], "completed")
        self.assertIn("task_executions", result["stages"])


if __name__ == "__main__":
    unittest.main()
