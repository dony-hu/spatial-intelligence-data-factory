import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.agent_runtime_store import AgentRuntimeStore

if "tools.agent_cli" not in sys.modules:
    agent_cli_stub = types.ModuleType("tools.agent_cli")
    agent_cli_stub.load_config = lambda *_args, **_kwargs: {}
    agent_cli_stub.parse_plan_from_answer = lambda *_args, **_kwargs: {}
    agent_cli_stub.run_requirement_query = lambda *_args, **_kwargs: {"answer": ""}
    sys.modules["tools.agent_cli"] = agent_cli_stub

import tools.agent_server as agent_server


class SpecialistMetadataAndAPILogTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="specialist_api_log_")
        self.db_path = str(Path(self.tmpdir) / "agent_runtime.db")
        self.base_dir = str(Path(self.tmpdir) / "runtime_store")
        self.store = AgentRuntimeStore(db_path=self.db_path, base_dir=self.base_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_list_api_call_logs_filters(self):
        self.store.log_api_call(
            api_name="web_search",
            request_json='{"q":"a"}',
            response_json='{"ok":true}',
            latency_ms=100,
            task_run_id="trun_1",
        )
        self.store.log_api_call(
            api_name="map_service",
            request_json='{"q":"b"}',
            response_json='{"ok":true}',
            latency_ms=120,
            task_run_id="trun_2",
        )
        items = self.store.list_api_call_logs(task_run_id="trun_1")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["api_name"], "web_search")

        items2 = self.store.list_api_call_logs(api_name="map_service")
        self.assertEqual(len(items2), 1)
        self.assertEqual(items2[0]["task_run_id"], "trun_2")

    def test_specialist_metadata_shape(self):
        agent_server.registry_initialized = False
        metadata = agent_server._build_specialist_metadata()
        self.assertGreaterEqual(len(metadata), 4)
        agents = {x.get("agent") for x in metadata}
        self.assertIn("process_expert", agents)
        self.assertIn("tool_registry", agents)
        self.assertTrue(all("health" in x for x in metadata))


if __name__ == "__main__":
    unittest.main()
