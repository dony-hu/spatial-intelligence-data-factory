"""
Simple HTTP Server for Factory Dashboard
使用 Python 标准库实现轻量级 Web 服务器（离线可用）
"""

import json
import sqlite3
import threading
import time
import inspect
from datetime import datetime
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
action_handlers = {}


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
            qs = parse_qs(parsed_path.query)
            line_id = qs.get("line_id", [""])[0].strip()
            case_name = qs.get("case_name", [""])[0].strip()
            try:
                highlight_seconds = int(qs.get("highlight_seconds", ["30"])[0])
            except (TypeError, ValueError):
                highlight_seconds = 30
            self.send_json_response(
                self._collect_graph_data(
                    line_id=line_id,
                    case_name=case_name,
                    highlight_seconds=highlight_seconds,
                )
            )
        elif path == "/api/line-details":
            line_id = parse_qs(parsed_path.query).get("line_id", [""])[0]
            self.send_json_response(self._get_line_details(line_id))
        elif path == "/":
            self.send_dashboard_html()
        else:
            self.send_error(404)

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        if path == "/api/actions/run-next-case":
            self._handle_action("run_next_case", self._read_json_body())
            return
        if path == "/api/actions/reset-environment":
            self._handle_action("reset_environment", self._read_json_body())
            return
        if path == "/api/actions/run-custom-address":
            self._handle_action("run_custom_address", self._read_json_body())
            return
        self.send_error(404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _handle_action(self, action_name: str, payload=None):
        fn = action_handlers.get(action_name)
        if not callable(fn):
            self.send_json_response({"status": "error", "error": f"Action not available: {action_name}"})
            return
        try:
            payload = payload or {}
            sig = inspect.signature(fn)
            if len(sig.parameters) == 0:
                result = fn()
            else:
                result = fn(payload)
            self.send_json_response(result if isinstance(result, dict) else {"status": "ok"})
        except Exception as exc:
            self.send_json_response({"status": "error", "error": str(exc)})

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

    def _parse_ts(self, value: str):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    def _collect_graph_data(self, line_id: str = "", case_name: str = "", highlight_seconds: int = 30):
        node_map = {}
        rel_map = {}
        recent_changes = []
        highlight_seconds = max(1, int(highlight_seconds or 30))
        now_epoch = time.time()
        history = factory_state.get("graph_change_log", [])
        details = factory_state.get("address_details", [])

        db_loaded = False
        runtime_db_path = str(factory_state.get("runtime_db_path", "") or "").strip()
        if runtime_db_path:
            try:
                source_filter = self._resolve_source_filter(history, line_id=line_id, case_name=case_name)
                db_nodes, db_rels = self._query_graph_from_db(
                    runtime_db_path,
                    source_filter=source_filter,
                    highlight_seconds=highlight_seconds,
                    now_epoch=now_epoch,
                )
                node_map = {n["node_id"]: n for n in db_nodes}
                rel_map = {r["relationship_id"]: r for r in db_rels}
                db_loaded = True
            except sqlite3.Error:
                db_loaded = False

        if not db_loaded:
            for item in details:
                detail = item.get("detail", {})
                detail_case_name = str(detail.get("case_name", item.get("case_name", ""))).strip()
                line_ids = [str(x.get("line_id", "")).strip() for x in (detail.get("line_results", []) or [])]

                if case_name and detail_case_name != case_name:
                    continue
                if line_id and line_id not in line_ids:
                    continue

                graph_output = detail.get("graph_output", {})
                item_ts = self._parse_ts(str(item.get("timestamp", "")))
                is_recent = bool(item_ts and (now_epoch - item_ts) <= highlight_seconds)

                for case_item in graph_output.get("graph_case_details", []):
                    for node in case_item.get("nodes", []):
                        node_id = str(node.get("node_id", "")).strip()
                        if node_id:
                            base = dict(node)
                            prev = node_map.get(node_id)
                            if prev:
                                base["is_recent"] = bool(prev.get("is_recent")) or is_recent
                            else:
                                base["is_recent"] = is_recent
                            node_map[node_id] = base
                    for rel in case_item.get("relationships", []):
                        rel_id = str(rel.get("relationship_id", "")).strip()
                        if rel_id:
                            base = dict(rel)
                            prev = rel_map.get(rel_id)
                            if prev:
                                base["is_recent"] = bool(prev.get("is_recent")) or is_recent
                            else:
                                base["is_recent"] = is_recent
                            rel_map[rel_id] = base

        if history:
            for h in history:
                h_case_name = str(h.get("case_name", "")).strip()
                h_line_ids = [str(x).strip() for x in (h.get("line_ids", []) or [])]
                if case_name and h_case_name != case_name:
                    continue
                if line_id and line_id not in h_line_ids:
                    continue
                h_ts = self._parse_ts(str(h.get("timestamp", "")))
                h_recent = bool(h_ts and (now_epoch - h_ts) <= highlight_seconds)
                recent_changes.append(
                    {
                        "addr_id": h.get("addr_id"),
                        "case_name": h_case_name,
                        "timestamp": h.get("timestamp"),
                        "nodes_merged": int(h.get("nodes_merged", 0) or 0),
                        "relationships_merged": int(h.get("relationships_merged", 0) or 0),
                        "is_recent": h_recent,
                    }
                )
        else:
            for item in details:
                detail = item.get("detail", {})
                detail_case_name = str(detail.get("case_name", item.get("case_name", ""))).strip()
                line_ids = [str(x.get("line_id", "")).strip() for x in (detail.get("line_results", []) or [])]
                if case_name and detail_case_name != case_name:
                    continue
                if line_id and line_id not in line_ids:
                    continue
                graph_output = detail.get("graph_output", {})
                merged_nodes = int(graph_output.get("graph_nodes_merged_total", 0) or 0)
                merged_rels = int(graph_output.get("graph_relationships_merged_total", 0) or 0)
                if merged_nodes <= 0 and merged_rels <= 0:
                    continue
                item_ts = self._parse_ts(str(item.get("timestamp", "")))
                is_recent = bool(item_ts and (now_epoch - item_ts) <= highlight_seconds)
                recent_changes.append(
                    {
                        "addr_id": item.get("addr_id"),
                        "case_name": detail_case_name,
                        "timestamp": item.get("timestamp"),
                        "nodes_merged": merged_nodes,
                        "relationships_merged": merged_rels,
                        "is_recent": is_recent,
                    }
                )

        return {
            "stats": {
                "total_nodes": len(node_map),
                "total_relationships": len(rel_map),
                "recent_nodes": sum(1 for x in node_map.values() if x.get("is_recent")),
                "recent_relationships": sum(1 for x in rel_map.values() if x.get("is_recent")),
            },
            "nodes": list(node_map.values()),
            "relationships": list(rel_map.values()),
            "recent_changes": recent_changes[-20:][::-1],
        }

    def _resolve_source_filter(self, history, line_id: str, case_name: str):
        if not case_name and not line_id:
            return None
        source_ids = set()
        for h in history:
            h_case_name = str(h.get("case_name", "")).strip()
            h_line_ids = [str(x).strip() for x in (h.get("line_ids", []) or [])]
            if case_name and h_case_name != case_name:
                continue
            if line_id and line_id not in h_line_ids:
                continue
            for sid in (h.get("source_ids", []) or []):
                s = str(sid).strip()
                if s:
                    source_ids.add(s)
        return source_ids

    def _query_graph_from_db(self, db_path: str, source_filter, highlight_seconds: int, now_epoch: float):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            if source_filter is not None:
                if not source_filter:
                    return [], []
                placeholders = ",".join(["?"] * len(source_filter))
                sids = list(source_filter)
                cur.execute(
                    f"SELECT node_id, node_type, name, properties, source_address, created_at FROM graph_nodes WHERE source_address IN ({placeholders}) ORDER BY created_at DESC LIMIT 500",
                    sids,
                )
                nodes = [dict(x) for x in cur.fetchall()]
                cur.execute(
                    f"SELECT relationship_id, source_node_id, target_node_id, relationship_type, properties, source_address, created_at FROM graph_relationships WHERE source_address IN ({placeholders}) ORDER BY created_at DESC LIMIT 1000",
                    sids,
                )
                relationships = [dict(x) for x in cur.fetchall()]
            else:
                cur.execute(
                    "SELECT node_id, node_type, name, properties, source_address, created_at FROM graph_nodes ORDER BY created_at DESC LIMIT 500"
                )
                nodes = [dict(x) for x in cur.fetchall()]
                cur.execute(
                    "SELECT relationship_id, source_node_id, target_node_id, relationship_type, properties, source_address, created_at FROM graph_relationships ORDER BY created_at DESC LIMIT 1000"
                )
                relationships = [dict(x) for x in cur.fetchall()]

            for n in nodes:
                ts = self._parse_ts(str(n.get("created_at", "")))
                n["is_recent"] = bool(ts and (now_epoch - ts) <= highlight_seconds)
            for r in relationships:
                ts = self._parse_ts(str(r.get("created_at", "")))
                r["is_recent"] = bool(ts and (now_epoch - ts) <= highlight_seconds)

            return nodes, relationships
        finally:
            conn.close()

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


def register_action_handlers(handlers: dict):
    action_handlers.clear()
    action_handlers.update(handlers or {})


if __name__ == "__main__":
    server, _ = start_server(port=5000)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.shutdown()
