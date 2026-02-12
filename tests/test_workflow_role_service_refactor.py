import tempfile
import unittest
from unittest.mock import MagicMock

from tools.factory_workflow import FactoryWorkflow


class WorkflowRoleServiceRefactorTests(unittest.TestCase):
    def test_workflow_has_split_role_services(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = f"{td}/factory.db"
            wf = FactoryWorkflow(factory_name="refactor-ut", db_path=db_path, init_production_lines=False)
            self.assertTrue(hasattr(wf, "director_service"))
            self.assertTrue(hasattr(wf, "process_expert_service"))
            self.assertTrue(hasattr(wf, "line_leader_service"))
            self.assertTrue(hasattr(wf, "worker_execution_service"))

    def test_workflow_delegates_pipeline_execution_to_worker_service(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = f"{td}/factory.db"
            wf = FactoryWorkflow(factory_name="refactor-ut-delegate", db_path=db_path, init_production_lines=False)
            worker_service = MagicMock()
            worker_service.execute_cleaning_pipeline.return_value = {"standardized_address": "上海市黄浦区中山东一路1号"}
            worker_service.execute_graph_pipeline.return_value = ([], [], {"pass": False, "reason": "x"}, {"nodes_merged": 0, "relationships_merged": 0, "nodes": [], "relationships": []})
            wf.worker_execution_service = worker_service

            order = MagicMock()
            spec = MagicMock()
            requirement = MagicMock()
            input_item = {"raw": "黄浦区中山东一路1号"}

            cleaning = wf._execute_cleaning_pipeline(order, spec, input_item, requirement)
            graph = wf._execute_graph_pipeline(order, spec, cleaning, requirement, "source_1")

            self.assertEqual(cleaning.get("standardized_address"), "上海市黄浦区中山东一路1号")
            self.assertEqual(graph[2].get("reason"), "x")
            worker_service.execute_cleaning_pipeline.assert_called_once()
            worker_service.execute_graph_pipeline.assert_called_once()

    def test_workflow_delegates_status_to_director_service(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = f"{td}/factory.db"
            wf = FactoryWorkflow(factory_name="refactor-ut-status", db_path=db_path, init_production_lines=False)
            director_service = MagicMock()
            director_service.get_factory_status.return_value = {"agent": "factory_director"}
            wf.director_service = director_service

            result = wf.get_factory_status()
            self.assertEqual(result.get("agent"), "factory_director")
            director_service.get_factory_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
