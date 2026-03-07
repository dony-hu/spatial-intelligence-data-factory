#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/database.postgres.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] missing env file: $ENV_FILE" >&2
  exit 2
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
else
  PY_BIN="python3"
fi

set -a
source "$ENV_FILE"
set +a

export TRUST_ALLOW_MEMORY_FALLBACK=0
export GOVERNANCE_ALLOW_MEMORY_FALLBACK=0

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[ERROR] DATABASE_URL is empty after loading $ENV_FILE" >&2
  exit 2
fi
if [[ -z "${GOVERNANCE_DB_LOCKED_URL:-}" ]]; then
  echo "[ERROR] GOVERNANCE_DB_LOCKED_URL is empty after loading $ENV_FILE" >&2
  exit 2
fi
if [[ "${DATABASE_URL}" != "${GOVERNANCE_DB_LOCKED_URL}" && "${GOVERNANCE_DB_SWITCH_CONFIRM:-0}" != "1" ]]; then
  echo "[ERROR] DB switch blocked: DATABASE_URL differs from GOVERNANCE_DB_LOCKED_URL and no manual confirmation." >&2
  exit 2
fi
if [[ "${DATABASE_URL}" != *":55432/"* ]]; then
  echo "[ERROR] DATABASE_URL must point to docker pg on :55432" >&2
  exit 2
fi
if [[ -z "${LLM_API_KEY:-}" ]]; then
  echo "[ERROR] LLM_API_KEY is empty. Export a real key before starting governance api." >&2
  exit 2
fi
if [[ "${LLM_API_KEY}" == "\${LLM_API_KEY}" ]]; then
  echo "[ERROR] LLM_API_KEY is unresolved placeholder string." >&2
  exit 2
fi

docker compose up -d postgres >/dev/null

exec "$PY_BIN" -m uvicorn services.governance_api.app.main:app --host 127.0.0.1 --port 8000 --log-level warning
