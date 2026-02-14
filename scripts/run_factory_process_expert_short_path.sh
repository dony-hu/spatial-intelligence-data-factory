#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/huda/Code/.venv/bin/python}"

cd "${ROOT}"

echo "[1/2] py_compile"
"${PYTHON_BIN}" -m py_compile \
  tools/address_toolpack_builder.py \
  tools/process_tools/design_process_tool.py \
  tools/process_tools/modify_process_tool.py \
  tests/test_factory_process_expert_short_path.py

echo "[2/2] run short-path tests"
export FACTORY_REAL_SHORT_PATH=1
echo "[INFO] REAL mode enabled: requires MAP_TOOLPACK_API_URL (+ optional MAP_TOOLPACK_API_KEY)"
if [[ -z "${MAP_TOOLPACK_API_URL:-}" ]]; then
  echo "[ERROR] MAP_TOOLPACK_API_URL is required in REAL mode."
  exit 2
fi

"${PYTHON_BIN}" -m unittest tests.test_factory_process_expert_short_path -v

echo "[DONE] factory process expert short-path tests passed"
