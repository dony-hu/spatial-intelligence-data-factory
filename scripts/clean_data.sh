#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

rm -rf "$ROOT/output/factory_templates"
rm -f "$ROOT/output/factory_story5_panel.log" "$ROOT/output/factory_story5_panel.pid"
rm -f "$ROOT/output/factory_process_dialog_room.log" "$ROOT/output/factory_process_dialog_room.pid"

echo "factory clean done"
