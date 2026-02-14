#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR"
export AGENT_RUNTIME="openhands"
export OPENHANDS_STRICT="1"
export GOVERNANCE_QUEUE_MODE="sync"
export LLM_CONFIG_PATH="${LLM_CONFIG_PATH:-$ROOT_DIR/config/llm_api.json}"

"/Users/huda/Code/.venv/bin/python" scripts/run_governance_e2e_minimal.py
