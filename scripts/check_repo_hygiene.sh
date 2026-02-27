#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[check] repo hygiene"

TRACKED_VENV_COUNT="$(git ls-files .venv | wc -l | tr -d ' ')"
if [[ "$TRACKED_VENV_COUNT" != "0" ]]; then
  echo "[blocked] .venv is still tracked by git: count=$TRACKED_VENV_COUNT"
  exit 2
fi

TRACKED_BROKEN_COUNT="$(git ls-files '.venv.broken*' | wc -l | tr -d ' ')"
if [[ "$TRACKED_BROKEN_COUNT" != "0" ]]; then
  echo "[blocked] .venv.broken* is still tracked by git: count=$TRACKED_BROKEN_COUNT"
  exit 2
fi

echo "[ok] no tracked venv artifacts"

echo "[check] sqlite runtime reflow guard"
SQLITE_SCAN_TARGETS=(services packages scripts tests)
SQLITE_PATTERNS=("sqlite://" "init_governance_sqlite" "sqlite3")
VIOLATION_FOUND=0

for pattern in "${SQLITE_PATTERNS[@]}"; do
  MATCHES="$(rg -n -S "$pattern" "${SQLITE_SCAN_TARGETS[@]}" \
    --glob '!scripts/check_repo_hygiene.sh' \
    --glob '!tests/test_repo_hygiene_gitignore.py' || true)"
  if [[ -n "$MATCHES" ]]; then
    echo "[blocked] sqlite runtime reference detected: pattern=$pattern"
    echo "$MATCHES"
    VIOLATION_FOUND=1
  fi
done

if [[ "$VIOLATION_FOUND" == "1" ]]; then
  echo "[hint] remove sqlite runtime references from mainline paths: services packages scripts tests"
  exit 2
fi

echo "[ok] no sqlite runtime references in mainline paths"
