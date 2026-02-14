#!/usr/bin/env python3
"""Story-5 panel server for aggregating two line outputs in factory project."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PANEL_HTML = PROJECT_ROOT / "templates" / "factory_lines_panel.html"

REPO_ADDRESS = Path("/Users/huda/Code/si-factory-public-security-address")
REPO_URBAN = Path("/Users/huda/Code/si-factory-urban-governance")

OUTPUT_MAP = {
    "public_security_address": REPO_ADDRESS / "output",
    "urban_governance": REPO_URBAN / "output",
}

state = {
    "updated_at": None,
    "lines": {
        "public_security_address": {"latest": None, "history": []},
        "urban_governance": {"latest": None, "history": []},
    },
}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _scan_line(line_code: str, out_dir: Path) -> None:
    if not out_dir.exists():
        state["lines"][line_code] = {"latest": None, "history": []}
        return

    files = sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    history = []
    for p in files[:20]:
        obj = _read_json(p)
        history.append(
            {
                "file": str(p),
                "name": p.name,
                "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                "type": (
                    "deploy_report"
                    if "deploy_report" in p.name
                    else "scene_graph"
                    if "scene_graph" in p.name
                    else "address_graph"
                    if "address_graph" in p.name
                    else "unknown"
                ),
                "payload": obj,
            }
        )

    latest = history[0] if history else None
    state["lines"][line_code] = {"latest": latest, "history": history}


def poll_outputs(interval: float = 3.0) -> None:
    while True:
        _scan_line("public_security_address", OUTPUT_MAP["public_security_address"])
        _scan_line("urban_governance", OUTPUT_MAP["urban_governance"])
        state["updated_at"] = datetime.now().isoformat()
        time.sleep(interval)


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, code=200):
        b = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            if not PANEL_HTML.exists():
                self._send_json({"error": f"panel html not found: {PANEL_HTML}"}, 500)
                return
            b = PANEL_HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        if path == "/api/summary":
            payload = {
                "updated_at": state["updated_at"],
                "lines": {
                    k: {
                        "history_count": len(v["history"]),
                        "latest_name": v["latest"]["name"] if v["latest"] else None,
                        "latest_mtime": v["latest"]["mtime"] if v["latest"] else None,
                    }
                    for k, v in state["lines"].items()
                },
            }
            self._send_json(payload)
            return

        if path.startswith("/api/line/") and path.endswith("/latest"):
            line_code = path.split("/")[3]
            line = state["lines"].get(line_code)
            if not line:
                self._send_json({"error": "line_not_found"}, 404)
                return
            self._send_json({"line": line_code, "latest": line["latest"]})
            return

        if path.startswith("/api/line/") and path.endswith("/history"):
            line_code = path.split("/")[3]
            line = state["lines"].get(line_code)
            if not line:
                self._send_json({"error": "line_not_found"}, 404)
                return
            self._send_json({"line": line_code, "history": line["history"]})
            return

        self._send_json({"error": "not_found"}, 404)


def main() -> None:
    t = threading.Thread(target=poll_outputs, daemon=True)
    t.start()

    server = HTTPServer(("127.0.0.1", 8866), Handler)
    print("factory-story5-panel: http://127.0.0.1:8866")
    server.serve_forever()


if __name__ == "__main__":
    main()
