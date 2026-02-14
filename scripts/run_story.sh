#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT"
python3 scripts/publish_line_panel_templates.py
python3 scripts/factory_process_dialog_room.py
