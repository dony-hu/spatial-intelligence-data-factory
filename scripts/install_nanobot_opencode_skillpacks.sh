#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$ROOT_DIR/workpackages/skills"
OPENCODE_AGENTS_DIR="$ROOT_DIR/.opencode/agents"

mkdir -p "$SKILLS_DIR" "$OPENCODE_AGENTS_DIR"

required_files=(
  "$SKILLS_DIR/nanobot_workpackage_schema_orchestrator.md"
  "$SKILLS_DIR/opencode_workpackage_builder_guardrails.md"
  "$SKILLS_DIR/trusted_map_api_catalog_sf_v1.md"
  "$OPENCODE_AGENTS_DIR/factory-workpackage-schema.md"
)

for f in "${required_files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "[ERROR] missing required skill/tool file: $f" >&2
    exit 1
  fi
done

echo "[OK] nanobot/opencode skillpacks are installed and ready."
echo "  - $SKILLS_DIR/nanobot_workpackage_schema_orchestrator.md"
echo "  - $SKILLS_DIR/opencode_workpackage_builder_guardrails.md"
echo "  - $SKILLS_DIR/trusted_map_api_catalog_sf_v1.md"
echo "  - $OPENCODE_AGENTS_DIR/factory-workpackage-schema.md"
