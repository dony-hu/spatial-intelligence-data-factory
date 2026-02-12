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

    def test_dashboard_graph_panels_use_multiline_rendering(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn(".graph-scroll", html)
        self.assertIn("white-space: pre-wrap;", html)

    def test_dashboard_has_graph_svg_renderer(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn('id="graphSvg"', html)
        self.assertIn("function renderGraphSvg(", html)

    def test_dashboard_has_dynamic_graph_runtime_state(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn("const graphRuntime", html)
        self.assertIn("function ingestGraphData(", html)

    def test_dashboard_graph_has_visible_node_and_edge_labels(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn("node-label", html)
        self.assertIn("edge-label", html)
        self.assertIn("relText.textContent", html)

    def test_dashboard_legend_matches_new_graph_model(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn(">building<", html)
        self.assertIn(">community<", html)
        self.assertIn(">unit<", html)
        self.assertIn(">room<", html)
        self.assertNotIn(">address<", html)

    def test_dashboard_has_manual_control_buttons(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn('id="btnRunNextCase"', html)
        self.assertIn('id="btnResetEnv"', html)
        self.assertIn('id="btnCustomCase"', html)
        self.assertIn("floating-controls", html)
        self.assertIn("/api/actions/run-next-case", html)
        self.assertIn("/api/actions/reset-environment", html)
        self.assertIn("/api/actions/run-custom-address", html)

    def test_dashboard_removes_graph_change_panel_and_places_recent_details_next_to_graph(self):
        html = (PROJECT_ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertNotIn("图谱变更流水", html)
        self.assertNotIn('id="graph-changes"', html)
        self.assertIn('id="graph-and-details"', html)
        self.assertIn('id="recent-details-panel"', html)
        self.assertIn("最近地址处理明细（前20条）", html)

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
