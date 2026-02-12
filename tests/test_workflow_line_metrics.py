import sqlite3
import sys
import tempfile
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.factory_workflow import FactoryWorkflow
from testdata.factory_demo_scenarios import get_all_scenarios


class WorkflowLineMetricsTests(unittest.TestCase):
    def test_line_metrics_updated_after_auto_execute(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "factory_test.db")
            wf = FactoryWorkflow(factory_name="test-factory-line-metrics", db_path=db_path)
            wf.approve_all_required_gates(approver="unit-test", note="test")

            scenario = get_all_scenarios()["quick_test"]()
            wf.submit_product_requirement(scenario)
            result = wf.create_production_workflow(scenario, auto_execute=True)

            self.assertEqual(result["status"], "completed")

            line_cleaning = wf.factory_state.get_production_line(FactoryWorkflow.ADDRESS_CLEANING_LINE_ID)
            line_graph = wf.factory_state.get_production_line(FactoryWorkflow.ADDRESS_TO_GRAPH_LINE_ID)

            self.assertIsNotNone(line_cleaning)
            self.assertIsNotNone(line_graph)

            expected = len(scenario.input_data)
            self.assertEqual(line_cleaning.completed_tasks, expected)
            self.assertEqual(line_graph.completed_tasks, expected)
            self.assertGreater(line_cleaning.total_tokens_consumed, 0.0)
            self.assertGreater(line_graph.total_tokens_consumed, 0.0)

            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT completed_tasks, total_tokens_consumed, status FROM production_lines WHERE line_id = ?",
                (FactoryWorkflow.ADDRESS_CLEANING_LINE_ID,),
            )
            row_clean = cur.fetchone()
            cur.execute(
                "SELECT completed_tasks, total_tokens_consumed, status FROM production_lines WHERE line_id = ?",
                (FactoryWorkflow.ADDRESS_TO_GRAPH_LINE_ID,),
            )
            row_graph = cur.fetchone()
            conn.close()

            self.assertEqual(row_clean[0], expected)
            self.assertEqual(row_graph[0], expected)
            self.assertGreater(row_clean[1], 0.0)
            self.assertGreater(row_graph[1], 0.0)
            self.assertEqual(row_clean[2], "idle")
            self.assertEqual(row_graph[2], "idle")


if __name__ == "__main__":
    unittest.main()
