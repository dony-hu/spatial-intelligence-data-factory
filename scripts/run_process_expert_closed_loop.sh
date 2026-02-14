#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8081}"
BASE_URL="http://127.0.0.1:${PORT}"

REQ_TEXT="${1:-请基于公安地址治理测试用例设计真实地址核实工艺，包含在线核实、冲突仲裁、证据链输出，并产出可发布工艺草案。}"

echo "[1/4] Health check: ${BASE_URL}/healthz"
curl -sS "${BASE_URL}/healthz" | jq .

echo "[2/4] Trigger process expert design"
DESIGN_RESP=$(curl -sS -X POST "${BASE_URL}/api/v1/process/expert/chat" \
  -H "Content-Type: application/json" \
  -d "$(jq -cn --arg req "$REQ_TEXT" '{action:"design", requirement:$req, domain:"verification"}')")

echo "$DESIGN_RESP" | jq .

DRAFT_ID=$(echo "$DESIGN_RESP" | jq -r '.draft_id // .tool_result.draft.draft_id // empty')
if [[ -z "$DRAFT_ID" ]]; then
  echo "[WARN] draft_id not found in response; stop here."
  exit 0
fi

echo "[3/4] Ask to publish draft (will likely return pending_confirmation)"
PUBLISH_REQ=$(jq -cn --arg msg "发布草案 draft_id=${DRAFT_ID}" --arg sid "session_closed_loop_$(date +%s)" '{action:"chat", session_id:$sid, message:$msg}')
PUBLISH_RESP=$(curl -sS -X POST "${BASE_URL}/api/v1/process/expert/chat" \
  -H "Content-Type: application/json" \
  -d "$PUBLISH_REQ")

echo "$PUBLISH_RESP" | jq .

CONFIRM_ID=$(echo "$PUBLISH_RESP" | jq -r '.tool_result.confirmation_id // empty')
if [[ -z "$CONFIRM_ID" ]]; then
  echo "[INFO] no confirmation required or no confirmation_id returned."
  exit 0
fi

echo "[4/4] Confirm write operation: ${CONFIRM_ID}"
CONFIRM_RESP=$(curl -sS -X POST "${BASE_URL}/api/v1/confirmation/respond" \
  -H "Content-Type: application/json" \
  -d "$(jq -cn --arg cid "$CONFIRM_ID" '{confirmation_id:$cid, response:"confirm"}')")

echo "$CONFIRM_RESP" | jq .

echo "[DONE] Closed-loop flow finished."
