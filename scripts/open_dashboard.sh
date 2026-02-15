#!/usr/bin/env bash
set -euo pipefail

if [[ "${ALLOW_DEMO_SCRIPTS:-0}" != "1" ]]; then
	echo "[blocked] scripts/open_dashboard.sh 已默认禁用（mock/demo流程）"
	echo "如需强制运行请设置: ALLOW_DEMO_SCRIPTS=1"
	echo "建议使用真实最小链路: ./scripts/run_governance_e2e_minimal.sh"
	exit 2
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${DEMO_PORT:-5054}"

cd "$ROOT_DIR"
DEMO_PORT="$PORT" ./scripts/factory_demo_daemon.sh restart
sleep 1
open "http://127.0.0.1:${PORT}"

echo "dashboard opened: http://127.0.0.1:${PORT}"
