#!/usr/bin/env python3
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web" / "dashboard"
DATA_DIR = PROJECT_ROOT / "output" / "dashboard"
OUTPUT_DIR = PROJECT_ROOT / "output"


class Handler(BaseHTTPRequestHandler):
    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404, "Not Found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            return self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        if self.path == "/static/app.js":
            return self._send_file(WEB_DIR / "app.js", "application/javascript; charset=utf-8")
        if self.path == "/static/styles.css":
            return self._send_file(WEB_DIR / "styles.css", "text/css; charset=utf-8")
        if self.path.startswith("/data/"):
            filename = self.path.split("/data/", 1)[1]
            safe_name = Path(filename).name
            target = DATA_DIR / safe_name
            suffix = target.suffix.lower()
            if suffix == ".md":
                content_type = "text/markdown; charset=utf-8"
            elif suffix == ".jsonl":
                content_type = "application/x-ndjson; charset=utf-8"
            else:
                content_type = "application/json; charset=utf-8"
            return self._send_file(target, content_type)
        if self.path.startswith("/artifacts/"):
            rel = self.path.split("/artifacts/", 1)[1]
            target = (OUTPUT_DIR / rel).resolve()
            try:
                target.relative_to(OUTPUT_DIR.resolve())
            except ValueError:
                self.send_error(403, "Forbidden")
                return
            suffix = target.suffix.lower()
            if suffix == ".md":
                content_type = "text/markdown; charset=utf-8"
            elif suffix == ".json":
                content_type = "application/json; charset=utf-8"
            else:
                content_type = "text/plain; charset=utf-8"
            return self._send_file(target, content_type)
        self.send_error(404, "Not Found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run dashboard web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8808)
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), Handler)
    print(f"dashboard_web: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
