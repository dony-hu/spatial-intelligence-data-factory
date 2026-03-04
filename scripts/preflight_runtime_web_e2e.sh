#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/database.postgres.env"
BASE_URL="${WEB_E2E_BASE_URL:-http://127.0.0.1:8000}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] missing env file: $ENV_FILE" >&2
  exit 2
fi

set -a
source "$ENV_FILE"
set +a

export TRUST_ALLOW_MEMORY_FALLBACK=0
export GOVERNANCE_ALLOW_MEMORY_FALLBACK=0

echo "[preflight] ensure docker postgres up..."
docker compose up -d postgres >/dev/null

echo "[preflight] check runtime preflight endpoint: $BASE_URL"
HTTP_CODE="$(curl -sS -o /tmp/runtime_preflight.json -w "%{http_code}" "$BASE_URL/v1/governance/observability/runtime/preflight?verify_llm=true&fail_fast=false")"
cat /tmp/runtime_preflight.json
echo
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "[ERROR] preflight HTTP $HTTP_CODE" >&2
  exit 1
fi

STATUS="$(python3 - <<'PY'
import json
from pathlib import Path
p=Path('/tmp/runtime_preflight.json')
data=json.loads(p.read_text(encoding='utf-8'))
print(str(data.get('status') or ''))
PY
)"

if [[ "$STATUS" != "ok" ]]; then
  echo "[ERROR] preflight status=$STATUS (see payload above)" >&2
  exit 1
fi

echo "[preflight] all checks passed."
