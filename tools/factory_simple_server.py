"""
Simple HTTP Server for Factory Dashboard
使用 Python 标准库实现轻量级 Web 服务器（离线可用）
"""

import json
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Global factory state
factory_state = {
    "factory_name": "Shanghai Data Factory",
    "status": "running",
    "start_time": None,
    "production_lines": {},
    "work_orders": {"total": 0, "completed": 0, "in_progress": 0, "pending": 0},
    "metrics": {"total_tokens": 0.0, "quality_rate": 0.0, "processed_count": 0},
}


class FactoryDashboardHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/api/status":
            self.send_json_response(factory_state)
        elif path == "/api/production-lines":
            self.send_json_response(factory_state.get("production_lines", {}))
        elif path == "/api/work-orders":
            self.send_json_response(factory_state.get("work_orders", {}))
        elif path == "/api/metrics":
            self.send_json_response(factory_state.get("metrics", {}))
        elif path == "/api/address-details":
            self.send_json_response({"address_details": factory_state.get("address_details", [])})
        elif path == "/api/graph-data":
            self.send_json_response({"nodes": self._collect_graph_nodes()})
        elif path == "/api/line-details":
            line_id = parse_qs(parsed_path.query).get("line_id", [""])[0]
            self.send_json_response(self._get_line_details(line_id))
        elif path == "/":
            self.send_dashboard_html()
        else:
            self.send_error(404)

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_dashboard_html(self):
        html = self.get_dashboard_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, fmt, *args):
        # keep console clean for live demos
        pass

    def _collect_graph_nodes(self):
        all_nodes = {}
        for item in factory_state.get("address_details", []):
            nodes = item.get("graph_result", {}).get("nodes", {})
            for node_id, node in nodes.items():
                all_nodes.setdefault(node_id, node)
        return all_nodes

    def _get_line_details(self, line_id: str) -> dict:
        details = factory_state.get("address_details", [])
        if line_id == "line_address_cleaning":
            return {
                "line_id": line_id,
                "line_name": "地址清洗产线",
                "addresses": [
                    {
                        "addr_id": d.get("addr_id"),
                        "raw": d.get("raw_address"),
                        "segment": d.get("cleaning_result", {}).get("segment_text", d.get("raw_address", "")),
                        "tokens": d.get("cleaning_result", {}).get("tokens_used", 0),
                        "status": d.get("status", "unknown"),
                    }
                    for d in details
                ],
            }
        if line_id == "line_address_to_graph":
            return {
                "line_id": line_id,
                "line_name": "地址-图谱产线",
                "addresses": [
                    {
                        "addr_id": d.get("addr_id"),
                        "raw": d.get("raw_address"),
                        "segment": d.get("graph_result", {}).get("segment_result", d.get("raw_address", "")),
                        "graph_nodes": d.get("graph_result", {}).get("nodes", {}),
                        "tokens": d.get("graph_result", {}).get("tokens_used", 0),
                        "status": d.get("status", "unknown"),
                    }
                    for d in details
                ],
            }
        return {}

    @staticmethod
    def get_dashboard_html():
        tpl = Path(__file__).resolve().parent.parent / "templates" / "dashboard.html"
        if tpl.exists():
            return tpl.read_text(encoding="utf-8")
        return "<html><body><h1>dashboard template not found</h1></body></html>"


def start_server(port=5000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, FactoryDashboardHandler)

    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print(f"✓ Dashboard server started at http://localhost:{port}")
    return httpd, factory_state


def update_factory_state(new_state):
    factory_state.update(new_state)


if __name__ == "__main__":
    server, _ = start_server(port=5000)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.shutdown()
