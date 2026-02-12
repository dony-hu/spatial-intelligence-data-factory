import sys
from pathlib import Path
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.spatial_entity_graph import SpatialEntityGraph
from tools.graph_visualizer import GraphVisualizer


class OfflineAssetTests(unittest.TestCase):
    def test_dashboard_template_has_no_cdn(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertNotIn("cdn.jsdelivr", html)
        self.assertNotIn("https://", html)

    def test_graph_visualizer_output_has_no_cdn(self):
        graph = SpatialEntityGraph("test")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "graph.html"
            GraphVisualizer(graph).generate_html(str(out))
            html = out.read_text(encoding="utf-8")
            self.assertNotIn("cdn.jsdelivr", html)
            self.assertNotIn("vis-network", html)


if __name__ == "__main__":
    unittest.main()
