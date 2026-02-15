#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HTML = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Process Expert Chat Panel</title>
  <style>
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; background: #0b1020; color: #e5e7eb; }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 16px; display: grid; grid-template-columns: 1.3fr 1fr; gap: 12px; }
    .card { background: #121a2f; border: 1px solid #26314f; border-radius: 10px; padding: 12px; }
    .title { font-weight: 700; margin-bottom: 8px; }
    #chat { height: 68vh; overflow: auto; background: #0f172a; border-radius: 8px; padding: 10px; border: 1px solid #26314f; }
    .msg { margin: 8px 0; white-space: pre-wrap; }
    .user { color: #93c5fd; }
    .assistant { color: #86efac; }
    .row { display: flex; gap: 8px; margin-top: 10px; }
    input, textarea, button, select { background: #0f172a; color: #e5e7eb; border: 1px solid #334155; border-radius: 8px; padding: 8px; }
    textarea { width: 100%; min-height: 90px; }
    button { cursor: pointer; }
    #raw { height: 68vh; overflow: auto; font-size: 12px; background: #0f172a; border: 1px solid #26314f; border-radius: 8px; padding: 10px; white-space: pre-wrap; }
    .hint { color: #94a3b8; font-size: 12px; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <div class=\"title\">Agent 对话（可介入）</div>
      <div class=\"hint\">通过 /api/v1/process/expert/chat(action=chat) 与 Agent 交互。支持确认类消息继续执行写操作。</div>
      <div id=\"chat\"></div>
      <div class=\"row\">
        <input id=\"sid\" style=\"flex:1\" placeholder=\"session_id（可不填自动生成）\" />
        <button onclick=\"newSession()\">新会话</button>
      </div>
      <div class=\"row\">
        <textarea id=\"msg\" placeholder=\"输入消息，例如：请基于当前审计失败项继续迭代，并给出下一轮改进方案\"></textarea>
      </div>
      <div class=\"row\">
        <button onclick=\"sendChat()\">发送 chat</button>
        <button onclick=\"sendDesign()\">发送 design</button>
      </div>
    </div>
    <div class=\"card\">
      <div class=\"title\">原始返回（Agent↔LLM可观测）</div>
      <div class=\"hint\">这里显示 API 完整 JSON，包括 llm_parser_answer/tool_result/operation_scripts。</div>
      <div id=\"raw\"></div>
    </div>
  </div>

<script>
let sessionId = 'panel_' + Math.random().toString(16).slice(2, 10);
document.getElementById('sid').value = sessionId;

function push(role, text) {
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = (role === 'user' ? '你: ' : 'Agent: ') + text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function setRaw(obj) {
  document.getElementById('raw').textContent = JSON.stringify(obj, null, 2);
}

function newSession() {
  sessionId = 'panel_' + Math.random().toString(16).slice(2, 10);
  document.getElementById('sid').value = sessionId;
  document.getElementById('chat').innerHTML = '';
  setRaw({session_id: sessionId});
}

async function send(payload) {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await resp.json();
  setRaw(data);
  return data;
}

async function sendChat() {
  const msg = document.getElementById('msg').value.trim();
  if (!msg) return;
  sessionId = document.getElementById('sid').value.trim() || sessionId;
  push('user', msg);
  const data = await send({action: 'chat', session_id: sessionId, message: msg});
  push('assistant', data.assistant_message || data.error || '(no response)');
}

async function sendDesign() {
  const req = document.getElementById('msg').value.trim();
  if (!req) return;
  push('user', '[design] ' + req);
  const data = await send({action: 'design', requirement: req, domain: 'verification'});
  push('assistant', data.status === 'ok' ? '设计完成: draft_id=' + (data.draft_id || ((data.tool_result||{}).draft&&data.tool_result.draft.draft_id) || 'N/A') : (data.error || 'failed'));
}
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    agent_base = "http://127.0.0.1:8081"

    def _send_json(self, payload: dict, status: int = 200) -> None:
        b = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _send_html(self, html: str) -> None:
        b = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_html(HTML)
            return
        if self.path == "/healthz":
            self._send_json({"status": "ok", "agent_base": self.agent_base})
            return
        self._send_json({"error": "not_found"}, 404)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self._send_json({"error": "not_found"}, 404)
            return
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_len)
            payload = json.loads(raw.decode("utf-8") if raw else "{}")
        except Exception as exc:
            self._send_json({"error": f"invalid_json: {exc}"}, 400)
            return

        endpoint = f"{self.agent_base.rstrip('/')}/api/v1/process/expert/chat"
        req = urllib.request.Request(
            endpoint,
            method="POST",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    obj = json.loads(body)
                except Exception:
                    obj = {"raw": body}
                self._send_json(obj, status=resp.getcode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                obj = json.loads(body)
            except Exception:
                obj = {"error": body}
            self._send_json(obj, status=exc.code)
        except Exception as exc:
            self._send_json({"error": str(exc), "agent_base": self.agent_base}, 500)


def main() -> int:
    parser = argparse.ArgumentParser(description="Process Expert interactive chat panel")
    parser.add_argument("--panel-port", type=int, default=8877)
    parser.add_argument("--agent-base", default="http://127.0.0.1:8081")
    args = parser.parse_args()

    Handler.agent_base = args.agent_base
    server = HTTPServer(("127.0.0.1", args.panel_port), Handler)
    print(f"process-expert-chat-panel: http://127.0.0.1:{args.panel_port} -> {args.agent_base}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
