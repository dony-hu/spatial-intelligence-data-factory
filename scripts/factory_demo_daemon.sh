#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/output/factory_demo_web.pid"
PORT_FILE="$ROOT_DIR/output/factory_demo_web.port"
LOG_FILE="$ROOT_DIR/output/factory_demo_web.log"
DEMO_PORT="${DEMO_PORT:-5000}"

start() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "already running (pid=$(cat "$PID_FILE"))"
    exit 0
  fi

  mkdir -p "$ROOT_DIR/output"

  if lsof -nP -iTCP:"$DEMO_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "port $DEMO_PORT already in use, set another port: DEMO_PORT=5050 $0 start"
    exit 1
  fi

  nohup python3 "$ROOT_DIR/scripts/factory_continuous_demo_web.py" \
    --host 127.0.0.1 \
    --port "$DEMO_PORT" \
    --case-mode scenario \
    --cases-per-cycle 30 \
    --max-cycles 0 \
    --case-interval 1.0 \
    --reset-interval 3.0 \
    --cleanup-each-cycle \
    >"$LOG_FILE" 2>&1 &

  echo $! > "$PID_FILE"
  echo "$DEMO_PORT" > "$PORT_FILE"
  sleep 1

  if kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "started (pid=$(cat "$PID_FILE"))"
    echo "dashboard: http://127.0.0.1:$DEMO_PORT"
    echo "log: $LOG_FILE"
  else
    echo "failed to start, check log: $LOG_FILE"
    rm -f "$PID_FILE" "$PORT_FILE"
    exit 1
  fi
}

stop() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "not running"
    exit 0
  fi

  pid="$(cat "$PID_FILE")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid"
    sleep 1
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" || true
    fi
  fi

  rm -f "$PID_FILE"
  rm -f "$PORT_FILE"
  echo "stopped"
}

status() {
  port="${DEMO_PORT}"
  if [[ -f "$PORT_FILE" ]]; then
    port="$(cat "$PORT_FILE")"
  fi
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
    echo "running (pid=$(cat "$PID_FILE"))"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
  else
    echo "stopped"
  fi
}

logs() {
  tail -n 120 "$LOG_FILE" 2>/dev/null || true
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop || true; start ;;
  status) status ;;
  logs) logs ;;
  *)
    echo "usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac
