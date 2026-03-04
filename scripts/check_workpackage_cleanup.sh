#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -x "./.venv/bin/pytest" ]]; then
  PYTEST_BIN="./.venv/bin/pytest"
else
  PYTEST_BIN="pytest"
fi

PYTHONPATH=. "${PYTEST_BIN}" -q \
  tests/test_workpackage_v1_cleanup_guard.py \
  tests/test_workpackage_blueprint_schema_versioning.py \
  tests/test_workpackage_schema_address_case_example.py \
  tests/test_workpackage_schema_companion_artifacts.py \
  tests/test_run_p0_workpackage.py
