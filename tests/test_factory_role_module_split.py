import unittest

from tools.factory_roles.director_service import DirectorService
from tools.factory_roles.process_expert_service import ProcessExpertService
from tools.factory_roles.production_line_leader_service import ProductionLineLeaderService
from tools.factory_roles.worker_execution_service import WorkerExecutionService


class FactoryRoleModuleSplitTests(unittest.TestCase):
    def test_each_role_service_in_its_own_module(self):
        self.assertEqual(DirectorService.__module__, "tools.factory_roles.director_service")
        self.assertEqual(ProcessExpertService.__module__, "tools.factory_roles.process_expert_service")
        self.assertEqual(ProductionLineLeaderService.__module__, "tools.factory_roles.production_line_leader_service")
        self.assertEqual(WorkerExecutionService.__module__, "tools.factory_roles.worker_execution_service")


if __name__ == "__main__":
    unittest.main()
