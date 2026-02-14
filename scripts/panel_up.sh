#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/output/factory_process_dialog_room.log"
PID="$ROOT/output/factory_process_dialog_room.pid"

mkdir -p "$ROOT/output"
python3 "$ROOT/scripts/publish_line_panel_templates.py" >/dev/null

if [[ -f "$PID" ]] && kill -0 "$(cat "$PID")" 2>/dev/null; then
  echo "factory panel already running: pid=$(cat "$PID")"
  echo "http://127.0.0.1:8866"
  exit 0
fi

nohup python3 "$ROOT/scripts/factory_process_dialog_room.py" >"$LOG" 2>&1 &
echo $! > "$PID"
sleep 1

echo "factory panel up: http://127.0.0.1:8877 (pid=$(cat "$PID"))"
