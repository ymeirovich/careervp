#!/usr/bin/env bash
# scripts/ui-upgrade/verify-spec.sh
# Run all pre-merge checks for a given spec before committing.
#
# Usage:
#   ./scripts/ui-upgrade/verify-spec.sh FE-UI-001
#   ./scripts/ui-upgrade/verify-spec.sh ALL   # run without spec filter
#
# Exit codes:
#   0  all checks passed
#   1  one or more checks failed

set -euo pipefail

SPEC_ID="${1:-}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
FRONTEND="$REPO_ROOT/src/frontend"

# ── Helpers ──────────────────────────────────────────────────────────────────

pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; }

section() {
  echo ""
  echo "── $1 ──────────────────────────────────────────"
}

banner() {
  echo ""
  echo "╔══════════════════════════════════════════════╗"
  echo "  $1"
  echo "╚══════════════════════════════════════════════╝"
}

# ── Validate input ────────────────────────────────────────────────────────────

if [[ -z "$SPEC_ID" ]]; then
  echo "Usage: $0 <SPEC-ID>   e.g.  $0 FE-UI-001"
  echo "       $0 ALL         # no spec filter"
  exit 1
fi

banner "Pre-merge checks — $SPEC_ID"

cd "$FRONTEND"

# ── 1. TypeScript ─────────────────────────────────────────────────────────────

section "TypeScript (tsc --noEmit)"
if npm run typecheck 2>&1; then
  pass "TypeScript clean"
else
  fail "TypeScript errors — fix before committing"
  exit 1
fi

# ── 2. Vitest UI unit tests ───────────────────────────────────────────────────

section "Vitest UI tests"
if npx vitest run --config vitest.config.ts --reporter verbose 2>&1; then
  pass "Vitest passed"
else
  fail "Vitest failures — fix before committing"
  exit 1
fi

# ── 3. Jest unit tests ────────────────────────────────────────────────────────

section "Jest unit tests"
if npm run test:unit -- --passWithNoTests 2>&1; then
  pass "Jest unit passed"
else
  fail "Jest unit failures — fix before committing"
  exit 1
fi

# ── 4. Spec status check ──────────────────────────────────────────────────────

if [[ "$SPEC_ID" != "ALL" ]]; then
  section "Spec status check"
  SPEC_FILE=$(find "$REPO_ROOT/docs/upgrade/specs" -name "${SPEC_ID}*.md" | head -1)

  if [[ -z "$SPEC_FILE" ]]; then
    fail "Spec file not found for $SPEC_ID"
    exit 1
  fi

  STATUS=$(grep "^status:" "$SPEC_FILE" | head -1 | awk '{print $2}')
  if [[ "$STATUS" == "implemented" ]]; then
    pass "Spec status = implemented ✓"
  elif [[ "$STATUS" == "validated" || "$STATUS" == "closed" ]]; then
    pass "Spec status = $STATUS (already past implemented)"
  else
    fail "Spec status is '$STATUS' — must be 'implemented' before committing"
    echo "     Update status: in docs/upgrade/specs/$(basename $SPEC_FILE)"
    exit 1
  fi

  # Warn if Traceability Matrix has TBD line references
  TBD_COUNT=$(grep -c ":TBD" "$SPEC_FILE" || true)
  if [[ "$TBD_COUNT" -gt 0 ]]; then
    echo "  ⚠  Traceability Matrix has $TBD_COUNT TBD line reference(s) — fill them in"
  fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────

banner "$SPEC_ID — ALL CHECKS PASSED — ready to commit"
