#!/usr/bin/env bash
set -euo pipefail

branch="${1:-$(git branch --show-current)}"

if [[ -z "${branch}" ]]; then
  echo "Error: could not determine current branch."
  exit 1
fi

if [[ "${branch}" == "main" ]]; then
  echo "Error: run this from a feature branch, not main."
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: gh CLI is required."
  exit 1
fi

if [[ -n "$(git status --short)" ]]; then
  echo "Error: working tree is not clean. Commit or stash changes first."
  exit 1
fi

git push -u origin "${branch}"

pr_number="$(gh pr list --head "${branch}" --base main --state open --json number --jq '.[0].number' || true)"

if [[ -z "${pr_number}" || "${pr_number}" == "null" ]]; then
  gh pr create --base main --head "${branch}" --fill
  pr_number="$(gh pr list --head "${branch}" --base main --state open --json number --jq '.[0].number')"
fi

if [[ -z "${pr_number}" || "${pr_number}" == "null" ]]; then
  echo "Error: unable to determine PR number for branch ${branch}."
  exit 1
fi

pr_state="$(gh pr view "${pr_number}" --json state --jq '.state')"
if [[ "${pr_state}" == "MERGED" ]]; then
  echo "PR #${pr_number} is already merged."
else
  # Do not use --delete-branch here: it can fail when main is checked out in another worktree.
  gh pr merge "${pr_number}" --merge
fi

merge_oid="$(gh pr view "${pr_number}" --json mergeCommit --jq '.mergeCommit.oid')"
if [[ -z "${merge_oid}" || "${merge_oid}" == "null" ]]; then
  echo "Error: PR #${pr_number} has no merge commit yet."
  exit 1
fi

git fetch origin main
if git merge-base --is-ancestor "${merge_oid}" origin/main; then
  echo "Verified: merge commit ${merge_oid} is on origin/main (PR #${pr_number})."
else
  echo "Error: merge commit ${merge_oid} not found on origin/main."
  exit 1
fi
