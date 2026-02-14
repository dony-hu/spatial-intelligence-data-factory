#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE_DIR="${1:-/Users/huda/Code/worktrees}"

cd "$ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "[WARN] 当前仓库有未提交改动。建议先提交后再开多线，避免分线基线不一致。"
fi

mkdir -p "$BASE_DIR"

create_or_attach() {
  local branch="$1"
  local path="$2"

  if [[ -d "$path/.git" || -f "$path/.git" ]]; then
    echo "[SKIP] worktree已存在: $path"
    return
  fi

  if git show-ref --verify --quiet "refs/heads/$branch"; then
    git worktree add "$path" "$branch"
  else
    git worktree add -b "$branch" "$path"
  fi

  echo "[OK] $branch -> $path"
}

create_or_attach "codex/orchestrator" "$BASE_DIR/orchestrator"
create_or_attach "codex/factory-process" "$BASE_DIR/factory-process"
create_or_attach "codex/factory-tooling" "$BASE_DIR/factory-tooling"
create_or_attach "codex/factory-workpackage" "$BASE_DIR/factory-workpackage"
create_or_attach "codex/factory-observability-gen" "$BASE_DIR/factory-observability-gen"
create_or_attach "codex/line-execution" "$BASE_DIR/line-execution"

echo

echo "[DONE] 多线工作区准备完成。"
echo "下一步：在客户端分别打开以上6个目录。"
