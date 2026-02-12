import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.factory_agents import Worker
from tools.factory_framework import ProcessStep, ProcessSpec, WorkOrder, WorkOrderStatus


class GraphModelingSpecTests(unittest.TestCase):
    def _dummy_order(self):
        spec = ProcessSpec(
            process_id="proc_graph_spec",
            process_name="graph_spec",
            steps=[ProcessStep.EXTRACTION],
            estimated_duration=1.0,
            required_workers=1,
            quality_rules={},
            resource_requirements={},
        )
        return WorkOrder(
            work_order_id="wo_graph_spec",
            requirement_id="req_graph_spec",
            product_name="graph_spec",
            process_spec=spec,
            assigned_line_id="line_graph_spec",
            status=WorkOrderStatus.PENDING,
        )

    def test_graph_payload_has_no_address_or_alias_node(self):
        worker = Worker("worker_graph_spec_1")
        order = self._dummy_order()
        execution = worker.execute_task(
            order,
            {
                "standardized_address": "上海市黄浦区中山东一路1号",
                "components": {
                    "city": "上海市",
                    "district": "黄浦区",
                    "road": "中山东一路",
                    "house_number": "1号",
                },
                "aliases": ["上海黄浦中山东路1号"],
            },
            ProcessStep.EXTRACTION,
        )
        nodes = execution.output_data.get("nodes", [])
        node_types = {n.get("type") for n in nodes}
        self.assertIn("building", node_types)
        self.assertNotIn("address", node_types)
        self.assertNotIn("alias", node_types)

    def test_graph_payload_supports_community_unit_room_hierarchy(self):
        worker = Worker("worker_graph_spec_2")
        order = self._dummy_order()
        execution = worker.execute_task(
            order,
            {
                "standardized_address": "上海市浦东新区世纪花园小区8号2单元301室",
                "components": {
                    "city": "上海市",
                    "district": "浦东新区",
                    "road": "世纪大道",
                    "community": "世纪花园小区",
                    "house_number": "8号",
                    "unit": "2单元",
                    "room": "301室",
                },
                "aliases": ["浦东世纪花园8号2单元301"],
            },
            ProcessStep.EXTRACTION,
        )
        nodes = execution.output_data.get("nodes", [])
        relationships = execution.output_data.get("relationships", [])
        node_types = {n.get("type") for n in nodes}
        self.assertTrue({"community", "building", "unit", "room"}.issubset(node_types))
        rel_types = {r.get("type") for r in relationships}
        self.assertIn("contains", rel_types)


if __name__ == "__main__":
    unittest.main()
