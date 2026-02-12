"""
Graph Visualizer - Generate offline HTML visualization of entity relationship graph
"""

import json
from typing import Dict, List
from datetime import datetime
from tools.spatial_entity_graph import SpatialEntityGraph, RelationshipType, EntityNodeType


class GraphVisualizer:
    """Generate offline-friendly HTML visualization (no CDN dependency)."""

    NODE_COLORS = {
        EntityNodeType.PROVINCE.value: "#FF6B6B",
        EntityNodeType.CITY.value: "#FF8C42",
        EntityNodeType.DISTRICT.value: "#FFD93D",
        EntityNodeType.STREET.value: "#6BCB77",
        EntityNodeType.LANE.value: "#4D96FF",
        EntityNodeType.BUILDING.value: "#9D4EDD",
        EntityNodeType.POI.value: "#3A86FF",
        EntityNodeType.LANDMARK.value: "#FB5607",
        EntityNodeType.ADDRESS.value: "#8338EC",
        EntityNodeType.FUSION_ENTITY.value: "#FFBE0B",
    }

    EDGE_COLORS = {
        RelationshipType.HIERARCHICAL.value: "#dc2626",
        RelationshipType.SPATIAL_CONTAINS.value: "#2563eb",
        RelationshipType.SPATIAL_ADJACENT.value: "#16a34a",
        RelationshipType.SPATIAL_NEAR.value: "#ea580c",
        RelationshipType.ENTITY_MAPPING.value: "#7c3aed",
        RelationshipType.MULTI_SOURCE_FUSION.value: "#92400e",
        RelationshipType.DATA_LINEAGE.value: "#6b7280",
    }

    def __init__(self, graph: SpatialEntityGraph):
        self.graph = graph

    def _nodes(self) -> List[Dict]:
        return [
            {
                "id": n.node_id,
                "label": n.name,
                "type": n.node_type.value,
                "color": self.NODE_COLORS.get(n.node_type.value, "#94a3b8"),
            }
            for n in self.graph.nodes.values()
        ]

    def _edges(self) -> List[Dict]:
        return [
            {
                "from": r.source_node_id,
                "to": r.target_node_id,
                "type": r.relationship_type.value,
                "color": self.EDGE_COLORS.get(r.relationship_type.value, "#64748b"),
            }
            for r in self.graph.relationships.values()
        ]

    def generate_html(self, output_file: str = "output/entity_relationship_graph.html"):
        nodes = self._nodes()
        edges = self._edges()
        stats = self.graph.get_graph_stats()

        # Render a compact adjacency list by node type for offline readability.
        grouped: Dict[str, List[str]] = {}
        for node in nodes:
            grouped.setdefault(node["type"], []).append(node["label"])

        group_rows = "".join(
            f"<tr><td style='color:{self.NODE_COLORS.get(t, '#334155')}'>{t}</td><td>{len(v)}</td><td>{', '.join(v[:10])}{' ...' if len(v) > 10 else ''}</td></tr>"
            for t, v in sorted(grouped.items())
        )

        edge_counts: Dict[str, int] = {}
        for edge in edges:
            edge_counts[edge["type"]] = edge_counts.get(edge["type"], 0) + 1
        edge_rows = "".join(
            f"<tr><td style='color:{self.EDGE_COLORS.get(t, '#334155')}'>{t}</td><td>{c}</td></tr>"
            for t, c in sorted(edge_counts.items())
        )

        html = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>空间实体关系图谱 - {self.graph.region}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 20px; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: linear-gradient(135deg,#f0f7ff 0%,#f7fbff 100%); color:#0f172a; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    .card {{ background: #fff; border: 1px solid #dbe7f3; border-radius: 12px; padding: 16px; margin-bottom: 14px; }}
    h1 {{ margin: 0 0 8px; color:#0f3c66; }}
    .sub {{ color:#425b76; font-size: 13px; }}
    .grid {{ display:grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); margin-top:10px; }}
    .metric {{ border:1px solid #dbe7f3; border-radius:10px; padding:12px; background:#f8fbff; }}
    .metric .k {{ color:#425b76; font-size:12px; }}
    .metric .v {{ font-size:26px; font-weight:700; color:#0f3c66; margin-top:6px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th, td {{ border-bottom:1px solid #e4edf7; text-align:left; padding:8px; vertical-align:top; }}
    th {{ color:#1f4f7a; }}
    code {{ background:#f1f5f9; padding:2px 6px; border-radius:6px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"card\">
      <h1>空间实体关系图谱（离线版）</h1>
      <div class=\"sub\">Region: {stats['region']} | Generated: {datetime.now().isoformat()}</div>
      <div class=\"grid\">
        <div class=\"metric\"><div class=\"k\">总节点数</div><div class=\"v\">{stats['total_nodes']}</div></div>
        <div class=\"metric\"><div class=\"k\">总关系数</div><div class=\"v\">{stats['total_relationships']}</div></div>
        <div class=\"metric\"><div class=\"k\">节点类型数</div><div class=\"v\">{len(stats['node_types'])}</div></div>
        <div class=\"metric\"><div class=\"k\">关系类型数</div><div class=\"v\">{len(stats['relationship_types'])}</div></div>
      </div>
    </section>

    <section class=\"card\">
      <h3>节点分布</h3>
      <table>
        <thead><tr><th>类型</th><th>数量</th><th>示例（最多10个）</th></tr></thead>
        <tbody>{group_rows}</tbody>
      </table>
    </section>

    <section class=\"card\">
      <h3>关系分布</h3>
      <table>
        <thead><tr><th>类型</th><th>数量</th></tr></thead>
        <tbody>{edge_rows}</tbody>
      </table>
    </section>

    <section class=\"card\">
      <h3>导出提示</h3>
      <p>如需结构化消费，请使用 <code>output/graph.json</code> 或 <code>output/graph.graphml</code>。</p>
    </section>

    <script>
      window.__GRAPH_DATA__ = {json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False)};
    </script>
  </div>
</body>
</html>
"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✓ HTML visualization generated: {output_file}")
        return output_file
