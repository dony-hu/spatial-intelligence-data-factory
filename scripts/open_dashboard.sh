#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${DEMO_PORT:-5054}"

cd "$ROOT_DIR"
DEMO_PORT="$PORT" ./scripts/factory_demo_daemon.sh restart
sleep 1
open "http://127.0.0.1:${PORT}"

echo "dashboard opened: http://127.0.0.1:${PORT}"
