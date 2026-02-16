#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-/Users/huda/Code/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[ERROR] PYTHON_BIN not executable: $PYTHON_BIN"
  exit 2
fi

PG_BIN_DIR="${PG_BIN_DIR:-/opt/homebrew/opt/postgresql@16/bin}"
if [[ ! -x "$PG_BIN_DIR/psql" ]]; then
  if command -v psql >/dev/null 2>&1; then
    PG_BIN_DIR="$(dirname "$(command -v psql)")"
  fi
fi
if [[ ! -x "$PG_BIN_DIR/psql" ]]; then
  echo "[ERROR] Cannot find psql. Set PG_BIN_DIR or install postgresql@16."
  exit 2
fi

export PATH="$PG_BIN_DIR:$PATH"

PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-$(whoami)}"
PG_DB="${PG_DB:-si_factory}"

export DATABASE_URL="${DATABASE_URL:-postgresql://${PG_USER}@${PG_HOST}:${PG_PORT}/${PG_DB}}"
export PYTHONPATH="$ROOT_DIR"

echo "[INFO] DATABASE_URL=$DATABASE_URL"
echo "[INFO] PG_BIN_DIR=$PG_BIN_DIR"

if command -v brew >/dev/null 2>&1; then
  brew services start postgresql@16 >/dev/null 2>&1 || true
fi

if ! "$PG_BIN_DIR/pg_isready" -h "$PG_HOST" -p "$PG_PORT" >/dev/null 2>&1; then
  echo "[ERROR] PostgreSQL is not ready at ${PG_HOST}:${PG_PORT}."
  echo "[HINT] Try: brew services restart postgresql@16"
  exit 2
fi

echo "[INFO] PostgreSQL is ready"

if ! "$PG_BIN_DIR/psql" "postgresql://${PG_USER}@${PG_HOST}:${PG_PORT}/postgres" -tAc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1; then
  "$PG_BIN_DIR/createdb" -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$PG_DB"
  echo "[OK] Created database: $PG_DB"
else
  echo "[OK] Database exists: $PG_DB"
fi

if ! "$PYTHON_BIN" -c "import psycopg2" >/dev/null 2>&1; then
  echo "[INFO] Installing psycopg2-binary"
  "$PYTHON_BIN" -m pip install psycopg2-binary
fi

"$PYTHON_BIN" scripts/init_governance_pg_schema.py
chmod +x scripts/run_governance_e2e_dual_real.sh
./scripts/run_governance_e2e_dual_real.sh "$@"

echo "[INFO] PostgreSQL acceptance snapshot"
"$PG_BIN_DIR/psql" "$DATABASE_URL" -c "select status, count(*) from addr_task_run group by status order by status;"
"$PG_BIN_DIR/psql" "$DATABASE_URL" -c "select count(*) as raw_rows from addr_raw;"
"$PG_BIN_DIR/psql" "$DATABASE_URL" -c "select count(*) as canonical_rows from addr_canonical;"

echo "[DONE] dual real e2e completed"
