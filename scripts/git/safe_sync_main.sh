#!/usr/bin/env bash
set -euo pipefail

if [[ -n "$(git status --short)" ]]; then
  echo "Error: working tree is not clean. Commit or stash changes first."
  exit 1
fi

sync_current_main() {
  git pull --ff-only
  echo "Local main synced in current worktree."
}

sync_external_main_worktree() {
  local main_path
  main_path="$(git worktree list --porcelain | awk '
    /^worktree / {wt=$2}
    /^branch refs\/heads\/main$/ {print wt}
  ' | head -n1)"

  if [[ -n "${main_path}" && -d "${main_path}" ]]; then
    git -C "${main_path}" pull --ff-only
    echo "Local main synced in worktree: ${main_path}"
    return 0
  fi

  if [[ -n "${main_path}" && ! -d "${main_path}" ]]; then
    echo "Pruning stale worktree entry for main (${main_path})..."
    git worktree prune
  fi

  return 1
}

if [[ "$(git branch --show-current)" == "main" ]]; then
  sync_current_main
  exit 0
fi

if sync_external_main_worktree; then
  exit 0
fi

git switch main
sync_current_main
