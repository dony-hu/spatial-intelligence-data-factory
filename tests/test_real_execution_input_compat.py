import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.factory_agents import Worker
from tools.factory_framework import ProcessStep, WorkOrderStatus, WorkOrder, ProcessSpec
from tools.factory_workflow import FactoryWorkflow
from testdata.factory_demo_scenarios import get_all_scenarios


class RealExecutionInputCompatTests(unittest.TestCase):
    def _dummy_order(self):
        spec = ProcessSpec(
            process_id="proc_ut",
            process_name="ut",
            steps=[ProcessStep.STANDARDIZATION],
            estimated_duration=1.0,
            required_workers=1,
            quality_rules={},
            resource_requirements={},
        )
        return WorkOrder(
            work_order_id="wo_ut",
            requirement_id="req_ut",
            product_name="ut",
            process_spec=spec,
            assigned_line_id="line_ut",
            status=WorkOrderStatus.PENDING,
        )

    def test_standardization_supports_address_field(self):
        w = Worker("worker_ut_1")
        order = self._dummy_order()
        execution = w.execute_task(order, {"address": "上海市黄浦区中山东一路10号"}, ProcessStep.STANDARDIZATION)
        self.assertTrue(execution.output_data.get("valid"))
        self.assertTrue(bool(execution.output_data.get("standardized_address")))

    def test_relationship_extraction_scenario_not_all_cleaning_fail(self):
        wf = FactoryWorkflow(factory_name="ut-factory-relationship")
        wf.approve_all_required_gates(approver="unit-test", note="test")

        scenario = get_all_scenarios()["relationship_extraction"]()
        wf.submit_product_requirement(scenario)
        result = wf.create_production_workflow(scenario, auto_execute=True)

        self.assertEqual(result["status"], "completed")
        stage = result.get("stages", {}).get("task_executions", {})
        self.assertGreater(stage.get("graph_nodes_total", 0), 0)
        self.assertGreater(stage.get("graph_relationships_total", 0), 0)
        failed = stage.get("failed_cases", [])
        cleaning_fail = [x for x in failed if x.get("stage") == "cleaning"]
        self.assertEqual(len(cleaning_fail), 0)


if __name__ == "__main__":
    unittest.main()
