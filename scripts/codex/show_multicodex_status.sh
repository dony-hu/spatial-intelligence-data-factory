#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "==== git worktree list ===="
git worktree list

echo
echo "==== 子线状态文件 ===="
for f in \
  coordination/status/overview.md \
  coordination/status/factory-process.md \
  coordination/status/factory-tooling.md \
  coordination/status/factory-workpackage.md \
  coordination/status/factory-observability-gen.md \
  coordination/status/line-execution.md; do
  echo "---- $f ----"
  if [[ -f "$f" ]]; then
    sed -n '1,40p' "$f"
  else
    echo "(missing)"
  fi
  echo
done
