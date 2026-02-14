import sys
import os
import json
import tempfile
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.factory_agents import Worker
from tools.factory_framework import ProcessStep, WorkOrderStatus, WorkOrder, ProcessSpec
from tools.factory_workflow import FactoryWorkflow
from testdata.factory_demo_scenarios import get_all_scenarios


class RealExecutionInputCompatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_toolpack = os.environ.get("FACTORY_ADDRESS_TOOLPACK_PATH")
        cls._tmp_dir = tempfile.TemporaryDirectory()
        cls._toolpack_path = Path(cls._tmp_dir.name) / "generated_toolpack.json"
        cls._toolpack_path.write_text(
            json.dumps(
                {
                    "version": "ut.generated.1",
                    "cities": [
                        {
                            "name": "上海市",
                            "aliases": ["上海"],
                            "districts": [
                                {"name": "黄浦区", "aliases": ["黄浦"]},
                                {"name": "浦东新区", "aliases": ["浦东"]},
                                {"name": "徐汇区", "aliases": ["徐汇"]},
                                {"name": "静安区", "aliases": ["静安"]},
                                {"name": "虹口区", "aliases": ["虹口"]},
                                {"name": "杨浦区", "aliases": ["杨浦"]},
                                {"name": "闵行区", "aliases": ["闵行"]},
                                {"name": "宝山区", "aliases": ["宝山"]},
                                {"name": "嘉定区", "aliases": ["嘉定"]},
                                {"name": "奉贤区", "aliases": ["奉贤"]},
                                {"name": "青浦区", "aliases": ["青浦"]},
                                {"name": "松江区", "aliases": ["松江"]}
                            ]
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.environ["FACTORY_ADDRESS_TOOLPACK_PATH"] = str(cls._toolpack_path)

    @classmethod
    def tearDownClass(cls):
        cls._tmp_dir.cleanup()
        if cls._old_toolpack is None:
            os.environ.pop("FACTORY_ADDRESS_TOOLPACK_PATH", None)
        else:
            os.environ["FACTORY_ADDRESS_TOOLPACK_PATH"] = cls._old_toolpack

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

    def test_standardization_without_toolpack_must_fail(self):
        prev = os.environ.pop("FACTORY_ADDRESS_TOOLPACK_PATH", None)
        try:
            w = Worker("worker_ut_no_toolpack")
            order = self._dummy_order()
            execution = w.execute_task(order, {"address": "上海市黄浦区中山东一路10号"}, ProcessStep.STANDARDIZATION)
            self.assertFalse(execution.output_data.get("valid"))
            self.assertEqual(execution.output_data.get("error_code"), "MISSING_TOOLPACK")
        finally:
            if prev is not None:
                os.environ["FACTORY_ADDRESS_TOOLPACK_PATH"] = prev

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
