import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.factory_continuous_demo_web import run_worker
from tools.factory_simple_server import factory_state


class ContinuousDemoCleanupTests(unittest.TestCase):
    def test_cleanup_each_cycle_clears_graph_change_log(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "runtime.db")
            factory_state["graph_change_log"] = [{"addr_id": 1, "nodes_merged": 1}]
            factory_state["address_details"] = [{"addr_id": 1}]

            args = SimpleNamespace(
                runtime_db=db_path,
                case_mode="scenario",
                cases_per_cycle=0,
                max_cycles=1,
                case_interval=0.0,
                reset_interval=0.0,
                cleanup_each_cycle=True,
            )
            run_worker(args, threading.Event())

            self.assertEqual(factory_state.get("address_details", []), [])
            self.assertEqual(factory_state.get("graph_change_log", []), [])


if __name__ == "__main__":
    unittest.main()
