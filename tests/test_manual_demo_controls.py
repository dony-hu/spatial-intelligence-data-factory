import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.factory_continuous_demo_web import ManualDemoController
from tools.factory_simple_server import factory_state


class ManualDemoControlsTests(unittest.TestCase):
    def setUp(self):
        self._old_state = dict(factory_state)

    def tearDown(self):
        factory_state.clear()
        factory_state.update(self._old_state)

    def test_run_next_case_appends_detail(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "runtime.db")
            c = ManualDemoController(runtime_db=db_path, case_mode="scenario")
            c.reset_environment()
            before = len(factory_state.get("address_details", []))
            result = c.run_next_case()
            after = len(factory_state.get("address_details", []))
            self.assertEqual(result.get("status"), "ok")
            self.assertEqual(after, before + 1)
            last = factory_state.get("address_details", [])[-1]
            self.assertEqual(last.get("detail", {}).get("input_count"), 1)

    def test_manual_controller_starts_with_clean_environment(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "runtime.db")
            # 先制造旧库残留
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS graph_nodes (node_id TEXT PRIMARY KEY, node_type TEXT, name TEXT, properties TEXT, source_address TEXT, created_at TEXT)")
            cur.execute("INSERT INTO graph_nodes (node_id, node_type, name, properties, source_address, created_at) VALUES ('old_n', 'city', '旧数据', '{}', 'legacy', '2026-02-12T00:00:00')")
            conn.commit()
            conn.close()

            c = ManualDemoController(runtime_db=db_path, case_mode="scenario")
            self.assertEqual(factory_state.get("address_details", []), [])
            self.assertEqual(factory_state.get("graph_change_log", []), [])

            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM graph_nodes")
            self.assertEqual(cur.fetchone()[0], 0)
            conn.close()

    def test_reset_environment_clears_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "runtime.db")
            c = ManualDemoController(runtime_db=db_path, case_mode="scenario")
            c.run_next_case()
            self.assertGreater(len(factory_state.get("address_details", [])), 0)
            self.assertTrue(os.path.exists(db_path))
            r = c.reset_environment()
            self.assertEqual(r.get("status"), "ok")
            self.assertEqual(factory_state.get("address_details", []), [])
            self.assertEqual(factory_state.get("graph_change_log", []), [])
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='graph_nodes'")
            self.assertIsNotNone(cur.fetchone())
            conn.close()

    def test_run_custom_address_case(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "runtime.db")
            c = ManualDemoController(runtime_db=db_path, case_mode="scenario")
            c.reset_environment()
            result = c.run_custom_address("上海市黄浦区中山东一路88号")
            self.assertEqual(result.get("status"), "ok")
            self.assertEqual(result.get("case_name"), "manual_input")
            last = factory_state.get("address_details", [])[-1]
            self.assertEqual(last.get("detail", {}).get("input_count"), 1)
            self.assertIn("中山东一路88号", last.get("raw_address", ""))


if __name__ == "__main__":
    unittest.main()
