"""
Graph Visualizer - Generate interactive HTML visualization of entity relationship graph
"""

import json
from typing import Dict, List
from datetime import datetime
from tools.spatial_entity_graph import SpatialEntityGraph, RelationshipType, EntityNodeType


class GraphVisualizer:
    """Generate interactive HTML visualization using vis.js"""

    # Color scheme for different node types
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
        EntityNodeType.FUSION_ENTITY.value: "#FFBE0B"
    }

    # Edge styles for different relationship types
    EDGE_STYLES = {
        RelationshipType.HIERARCHICAL.value: {"color": "red", "dashes": False},
        RelationshipType.SPATIAL_CONTAINS.value: {"color": "blue", "dashes": False},
        RelationshipType.SPATIAL_ADJACENT.value: {"color": "green", "dashes": True},
        RelationshipType.SPATIAL_NEAR.value: {"color": "orange", "dashes": [5, 5]},
        RelationshipType.ENTITY_MAPPING.value: {"color": "purple", "dashes": False},
        RelationshipType.MULTI_SOURCE_FUSION.value: {"color": "brown", "dashes": False},
        RelationshipType.DATA_LINEAGE.value: {"color": "gray", "dashes": [10, 5]}
    }

    def __init__(self, graph: SpatialEntityGraph):
        self.graph = graph

    def generate_nodes_json(self) -> List[Dict]:
        """Generate nodes array for vis.js"""
        nodes = []

        for node in self.graph.nodes.values():
            node_dict = {
                "id": node.node_id,
                "label": node.name,
                "title": f"{node.node_type.value}: {node.name}",
                "color": self.NODE_COLORS.get(node.node_type.value, "#CCCCCC"),
                "font": {"size": 12},
                "shape": "dot",
                "size": max(15, min(50, 15 + node.confidence * 20)),
                "metadata": {
                    "type": node.node_type.value,
                    "level": node.level,
                    "confidence": node.confidence,
                    "lat": node.latitude,
                    "lon": node.longitude
                }
            }
            nodes.append(node_dict)

        return nodes

    def generate_edges_json(self) -> List[Dict]:
        """Generate edges array for vis.js"""
        edges = []

        for rel in self.graph.relationships.values():
            style = self.EDGE_STYLES.get(rel.relationship_type.value, {"color": "black", "dashes": False})
            edge_dict = {
                "from": rel.source_node_id,
                "to": rel.target_node_id,
                "label": rel.relationship_type.value,
                "title": f"{rel.relationship_type.value} (confidence: {rel.confidence:.2f})",
                "color": style["color"],
                "dashes": style.get("dashes", False),
                "arrows": "to",
                "smooth": {"type": "continuous"},
                "font": {"size": 10, "color": "gray"},
                "metadata": {
                    "type": rel.relationship_type.value,
                    "confidence": rel.confidence
                }
            }
            edges.append(edge_dict)

        return edges

    def generate_statistics_html(self) -> str:
        """Generate statistics section HTML"""
        stats = self.graph.get_graph_stats()

        html = """
        <div class="statistics">
            <h3>Graph Statistics</h3>
            <table>
                <tr>
                    <td><strong>Total Nodes:</strong></td>
                    <td>{}</td>
                </tr>
                <tr>
                    <td><strong>Total Edges:</strong></td>
                    <td>{}</td>
                </tr>
                <tr>
                    <td><strong>Region:</strong></td>
                    <td>{}</td>
                </tr>
            </table>

            <h4>Node Types Distribution</h4>
            <table>
        """.format(
            stats["total_nodes"],
            stats["total_relationships"],
            stats["region"]
        )

        for node_type, count in stats["node_types"].items():
            if count > 0:
                html += f"""
                <tr>
                    <td style="color: {self.NODE_COLORS.get(node_type, '#CCCCCC')}">
                        ■ {node_type}:
                    </td>
                    <td>{count}</td>
                </tr>
                """

        html += """
            </table>

            <h4>Relationship Types Distribution</h4>
            <table>
        """

        for rel_type, count in stats["relationship_types"].items():
            if count > 0:
                color = self.EDGE_STYLES.get(rel_type, {}).get("color", "black")
                html += f"""
                <tr>
                    <td style="color: {color}">● {rel_type}:</td>
                    <td>{count}</td>
                </tr>
                """

        html += """
            </table>
        </div>
        """

        return html

    def generate_legend_html(self) -> str:
        """Generate legend HTML"""
        html = """
        <div class="legend">
            <h3>Legend</h3>

            <h4>Node Types</h4>
            <div class="legend-items">
        """

        for node_type, color in self.NODE_COLORS.items():
            html += f"""
                <div class="legend-item">
                    <span class="legend-color" style="background-color: {color}"></span>
                    <span>{node_type}</span>
                </div>
            """

        html += """
            </div>

            <h4>Relationship Types</h4>
            <div class="legend-items">
        """

        for rel_type in RelationshipType:
            style = self.EDGE_STYLES.get(rel_type.value, {})
            color = style.get("color", "black")
            dashes = style.get("dashes", False)
            dash_style = "dashed" if dashes else "solid"

            html += f"""
                <div class="legend-item">
                    <svg width="30" height="2" style="margin-right: 10px; border-bottom: 2px {dash_style} {color}">
                    </svg>
                    <span>{rel_type.value}</span>
                </div>
            """

        html += """
            </div>
        </div>
        """

        return html

    def generate_html(self, output_file: str = "output/entity_relationship_graph.html"):
        """Generate complete interactive HTML visualization"""

        nodes = self.generate_nodes_json()
        edges = self.generate_edges_json()
        stats_html = self.generate_statistics_html()
        legend_html = self.generate_legend_html()

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spatial Entity Relationship Graph - {self.graph.region}</title>
    <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .content {{
            display: flex;
            height: calc(100vh - 200px);
        }}

        #graph {{
            flex: 1;
            border-right: 1px solid #ddd;
            background: linear-gradient(to bottom, #f9f9f9, #ffffff);
        }}

        .sidebar {{
            width: 350px;
            overflow-y: auto;
            padding: 20px;
            background: #f9f9f9;
        }}

        .sidebar h3 {{
            color: #667eea;
            margin-top: 20px;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            font-size: 1.2em;
        }}

        .sidebar h4 {{
            color: #764ba2;
            margin-top: 15px;
            margin-bottom: 10px;
            font-size: 1em;
        }}

        .statistics {{
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}

        .statistics table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .statistics table tr {{
            border-bottom: 1px solid #eee;
        }}

        .statistics table td {{
            padding: 8px;
        }}

        .statistics table td:first-child {{
            font-weight: bold;
            width: 60%;
        }}

        .legend {{
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}

        .legend-items {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            font-size: 0.95em;
        }}

        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
            border: 1px solid #ddd;
        }}

        .info-box {{
            background: #e8f4f8;
            border-left: 4px solid #667eea;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 0.95em;
        }}

        .info-box strong {{
            color: #667eea;
        }}

        .footer {{
            background: #f0f0f0;
            padding: 15px 30px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}

        /* Responsive */
        @media (max-width: 1200px) {{
            .content {{
                flex-direction: column;
            }}

            .sidebar {{
                width: 100%;
                height: auto;
                border-right: none;
                border-top: 1px solid #ddd;
            }}

            #graph {{
                min-height: 400px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ Spatial Entity Relationship Graph</h1>
            <p>Address Data Structure Analysis - {self.graph.region} Region</p>
        </div>

        <div class="content">
            <div id="graph"></div>
            <div class="sidebar">
                {self.generate_statistics_html()}
                {self.generate_legend_html()}
                <div class="info-box">
                    <strong>💡 Interaction Tips:</strong><br>
                    • Drag to move nodes<br>
                    • Scroll to zoom<br>
                    • Click to highlight<br>
                    • Hover for details
                </div>
            </div>
        </div>

        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
            Entity Relationship Graph Visualizer | Total Nodes: {len(nodes)} | Total Edges: {len(edges)}
        </div>
    </div>

    <script type="text/javascript">
        // Data for the graph
        var nodes = new vis.DataSet({json.dumps(nodes)});
        var edges = new vis.DataSet({json.dumps(edges)});

        var container = document.getElementById('graph');
        var data = {{
            nodes: nodes,
            edges: edges
        }};

        var options = {{
            physics: {{
                enabled: true,
                stabilization: {{
                    iterations: 200
                }},
                barnesHut: {{
                    gravitationalConstant: -80000,
                    centralGravity: 0.3,
                    springLength: 200,
                    springConstant: 0.08
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                navigationButtons: true,
                keyboard: true
            }},
            nodes: {{
                borderWidth: 2,
                borderWidthSelected: 4,
                shadow: {{
                    enabled: true,
                    color: 'rgba(0,0,0,0.3)',
                    size: 10,
                    x: 5,
                    y: 5
                }}
            }},
            edges: {{
                smooth: {{
                    type: 'continuous'
                }},
                shadow: {{
                    enabled: true,
                    color: 'rgba(0,0,0,0.2)',
                    size: 10,
                    x: 5,
                    y: 5
                }}
            }}
        }};

        var network = new vis.Network(container, data, options);

        // Fit to view on load
        setTimeout(function() {{
            network.fit();
        }}, 1000);

        // Log stats
        console.log('Graph Statistics:');
        console.log('Total Nodes:', nodes.length);
        console.log('Total Edges:', edges.length);
    </script>
</body>
</html>
        """

        # Write to file
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✓ HTML visualization generated: {output_file}")
        return output_file
