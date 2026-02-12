import sys
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.factory_simple_server import FactoryDashboardHandler, factory_state


class GraphDataFilterAndHighlightTests(unittest.TestCase):
    def setUp(self):
        self._old = list(factory_state.get("address_details", []))
        self._old_graph_change_log = list(factory_state.get("graph_change_log", []))
        now = datetime.now()
        ts_recent = now.isoformat()
        ts_old = (now - timedelta(seconds=120)).isoformat()

        factory_state["address_details"] = [
            {
                "addr_id": 1,
                "case_name": "quick_test",
                "timestamp": ts_recent,
                "detail": {
                    "case_name": "quick_test",
                    "line_results": [{"line_id": "line_address_cleaning"}, {"line_id": "line_address_to_graph"}],
                    "graph_output": {
                        "graph_nodes_merged_total": 2,
                        "graph_relationships_merged_total": 1,
                        "graph_case_details": [
                            {
                                "source_id": "s1",
                                "nodes": [
                                    {"node_id": "n1", "node_type": "city", "name": "上海市"},
                                    {"node_id": "n2", "node_type": "district", "name": "黄浦区"},
                                ],
                                "relationships": [
                                    {"relationship_id": "r1", "relationship_type": "contains", "source_node_id": "n1", "target_node_id": "n2"}
                                ],
                            }
                        ],
                    },
                },
            },
            {
                "addr_id": 2,
                "case_name": "relationship_extraction",
                "timestamp": ts_old,
                "detail": {
                    "case_name": "relationship_extraction",
                    "line_results": [{"line_id": "line_address_to_graph"}],
                    "graph_output": {
                        "graph_nodes_merged_total": 1,
                        "graph_relationships_merged_total": 1,
                        "graph_case_details": [
                            {
                                "source_id": "s2",
                                "nodes": [{"node_id": "n3", "node_type": "address", "name": "上海市徐汇区淮海中路1000号"}],
                                "relationships": [
                                    {"relationship_id": "r2", "relationship_type": "contains", "source_node_id": "n2", "target_node_id": "n3"}
                                ],
                            }
                        ],
                    },
                },
            },
        ]
        self.handler = object.__new__(FactoryDashboardHandler)

    def tearDown(self):
        factory_state["address_details"] = self._old
        factory_state["graph_change_log"] = self._old_graph_change_log

    def test_filter_by_case_name(self):
        data = self.handler._collect_graph_data(case_name="quick_test")
        self.assertEqual(data["stats"]["total_nodes"], 2)
        self.assertEqual(data["stats"]["total_relationships"], 1)

    def test_filter_by_line_id(self):
        data = self.handler._collect_graph_data(line_id="line_address_cleaning")
        self.assertEqual(data["stats"]["total_nodes"], 2)
        self.assertEqual(data["stats"]["total_relationships"], 1)

    def test_highlight_recent_nodes(self):
        data = self.handler._collect_graph_data(highlight_seconds=30)
        nodes = data["nodes"]
        node_recent_map = {n["node_id"]: n.get("is_recent") for n in nodes}
        self.assertTrue(node_recent_map["n1"])
        self.assertTrue(node_recent_map["n2"])
        self.assertFalse(node_recent_map["n3"])

    def test_recent_changes_use_history_log_and_keep_latest_first(self):
        factory_state["graph_change_log"] = [
            {"addr_id": 1, "case_name": "a", "timestamp": "2026-02-12T10:00:00", "nodes_merged": 1, "relationships_merged": 1, "is_recent": False},
            {"addr_id": 2, "case_name": "b", "timestamp": "2026-02-12T10:00:01", "nodes_merged": 2, "relationships_merged": 2, "is_recent": False},
            {"addr_id": 3, "case_name": "c", "timestamp": "2026-02-12T10:00:02", "nodes_merged": 3, "relationships_merged": 3, "is_recent": False},
        ]
        data = self.handler._collect_graph_data()
        changes = data["recent_changes"]
        self.assertEqual(len(changes), 3)
        self.assertEqual(changes[0]["addr_id"], 3)
        self.assertEqual(changes[1]["addr_id"], 2)
        self.assertEqual(changes[2]["addr_id"], 1)

    def test_graph_data_reads_nodes_relationships_from_sqlite(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = str(Path(td) / "runtime.db")
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE graph_nodes (node_id TEXT PRIMARY KEY, node_type TEXT, name TEXT, properties TEXT, source_address TEXT, created_at TEXT)"
            )
            cur.execute(
                "CREATE TABLE graph_relationships (relationship_id TEXT PRIMARY KEY, source_node_id TEXT, target_node_id TEXT, relationship_type TEXT, properties TEXT, source_address TEXT, created_at TEXT)"
            )
            cur.execute(
                "INSERT INTO graph_nodes (node_id, node_type, name, properties, source_address, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("db_n1", "city", "上海市", "{}", "s-db-1", datetime.now().isoformat()),
            )
            cur.execute(
                "INSERT INTO graph_relationships (relationship_id, source_node_id, target_node_id, relationship_type, properties, source_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("db_r1", "db_n1", "db_n1", "self", "{}", "s-db-1", datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()

            factory_state["runtime_db_path"] = db_path
            data = self.handler._collect_graph_data()
            node_ids = {n["node_id"] for n in data["nodes"]}
            rel_ids = {r["relationship_id"] for r in data["relationships"]}
            self.assertIn("db_n1", node_ids)
            self.assertIn("db_r1", rel_ids)


if __name__ == "__main__":
    unittest.main()
