import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class GraphCaseDataset1000Tests(unittest.TestCase):
    def test_dataset_exists_and_has_1000_cases(self):
        path = PROJECT_ROOT / "testdata" / "fixtures" / "address-graph-cases-1000-2026-02-12.json"
        self.assertTrue(path.exists(), f"missing dataset: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
        self.assertEqual(len(cases), 1000)

    def test_dataset_matches_new_graph_model_contract(self):
        path = PROJECT_ROOT / "testdata" / "fixtures" / "address-graph-cases-1000-2026-02-12.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
        patterns = set()

        for item in cases:
            self.assertIn("case_id", item)
            self.assertIn("category", item)
            self.assertIn("graph_pattern", item)
            self.assertIn("input", item)
            self.assertIn("expected", item)
            patterns.add(item.get("graph_pattern"))

            expected = item.get("expected", {})
            self.assertIn("forbidden_node_types", expected)
            self.assertIn("address", expected["forbidden_node_types"])
            self.assertIn("alias", expected["forbidden_node_types"])

        self.assertIn("road_building", patterns)
        self.assertIn("road_community_building", patterns)
        self.assertIn("road_community_building_unit_room", patterns)
        self.assertIn("invalid", patterns)


if __name__ == "__main__":
    unittest.main()
