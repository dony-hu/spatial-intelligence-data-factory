#!/usr/bin/env python3
"""Factory process dialog room for process-expert collaboration."""

from __future__ import annotations

import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

ROOM_STATE = {
    "updated_at": None,
    "messages": [],
}

HTML = """
<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>工厂工艺专家对话室</title>
  <style>
    body { font-family: \"PingFang SC\", \"Microsoft YaHei\", sans-serif; margin: 20px; background:#f3f7fb; color:#17324f; }
    .wrap { max-width: 900px; margin: 0 auto; }
    .card { background:#fff; border:1px solid #d7e4f2; border-radius:10px; padding:14px; margin-bottom:12px; }
    textarea { width:100%; min-height:90px; border:1px solid #cddced; border-radius:8px; padding:8px; }
    button { background:#1f5a8f; color:#fff; border:none; border-radius:8px; padding:8px 12px; cursor:pointer; }
    pre { background:#f7fbff; border:1px solid #e2ecf7; border-radius:8px; padding:12px; white-space:pre-wrap; max-height:420px; overflow:auto; }
    .meta { color:#4b6580; font-size:12px; }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <h2>工厂工艺专家对话室</h2>
      <p class=\"meta\">用于工艺 Story 的修订建议、步骤编排、验收标准对齐。</p>
      <textarea id=\"prompt\">请给出地址治理产线下一轮工艺优化建议（步骤、风险、验收）。</textarea>
      <br/><br/>
      <button onclick=\"sendMsg()\">发送</button>
    </div>
    <div class=\"card\">
      <h3>对话记录</h3>
      <pre id=\"history\"></pre>
    </div>
  </div>
<script>
async function refresh(){
  const r = await fetch('/api/history');
  const j = await r.json();
  document.getElementById('history').textContent = JSON.stringify(j, null, 2);
}
async function sendMsg(){
  const prompt = document.getElementById('prompt').value;
  await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({prompt})});
  await refresh();
}
setInterval(refresh, 4000);
refresh();
</script>
</body>
</html>
"""


def expert_reply(prompt: str) -> str:
    prompt = prompt.strip()
    return (
        "工艺专家建议:\n"
        "1) 明确输入契约与错误码映射；\n"
        "2) 将步骤拆为清洗/验证/图谱构建三段并记录耗时；\n"
        "3) 为失败样本增加回放队列；\n"
        "4) 验收以质量分、成功率、回放恢复率三指标收敛。\n"
        f"（本次需求摘要：{prompt[:80]}）"
    )


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload, code=200):
        b = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            b = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        if path == "/api/history":
            self._json(ROOM_STATE)
            return
        self._json({"error": "not_found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/chat":
            self._json({"error": "not_found"}, 404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size).decode("utf-8") or "{}")
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            self._json({"error": "prompt_required"}, 400)
            return
        message = {
            "at": datetime.now().isoformat(),
            "prompt": prompt,
            "reply": expert_reply(prompt),
        }
        ROOM_STATE["messages"].append(message)
        ROOM_STATE["updated_at"] = message["at"]
        self._json(message)


def main():
    server = HTTPServer(("127.0.0.1", 8877), Handler)
    print("factory-process-dialog-room: http://127.0.0.1:8877")
    server.serve_forever()


if __name__ == "__main__":
    main()
