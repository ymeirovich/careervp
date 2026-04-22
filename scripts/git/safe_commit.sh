#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <commit-message>"
  exit 1
fi

commit_message="$1"

if ! command -v pre-commit >/dev/null 2>&1; then
  echo "Error: pre-commit is not installed."
  exit 1
fi

# Always stage first so hooks evaluate the current full change set.
git add -A

if [[ -z "$(git diff --cached --name-only)" ]]; then
  echo "No staged changes to commit."
  exit 0
fi

# First pass may rewrite files (e.g., ruff-format). If it fails, restage and rerun once.
if ! pre-commit run; then
  echo "Pre-commit modified or rejected changes. Restaging and retrying once..."
  git add -A
  pre-commit run
fi

git commit -m "${commit_message}"
echo "Commit created successfully."
