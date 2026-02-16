#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$ROOT_DIR/../.venv/bin/python" ]]; then
  PY_BIN="$ROOT_DIR/../.venv/bin/python"
else
  PY_BIN="python3"
fi

"$PY_BIN" -m pytest tests/web_e2e -q "$@"
