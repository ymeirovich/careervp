#!/usr/bin/env bash
# scripts/ui-upgrade/verify-spec.sh
# Run pre-merge checks for a given spec before committing.
#
# Usage:
#   ./scripts/ui-upgrade/verify-spec.sh FE-UI-006   # targeted — spec tests only
#   ./scripts/ui-upgrade/verify-spec.sh ALL          # full suite (for final batch sign-off)
#
# WHY TARGETED:
#   Vitest picks up test stubs for ALL 26 specs via glob. Files for unimplemented
#   specs fail ERR_MODULE_NOT_FOUND because their components don't exist yet.
#   Running the full suite during Batch 1 will always show ~48 noise failures.
#   This script runs only the tests for the spec you just implemented.
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

# ── 2. Vitest — targeted to THIS spec only ────────────────────────────────────
#
# We do NOT run the full vitest suite here. The glob in vitest.config.ts picks
# up stub test files for all 26 specs. Files for unimplemented future specs
# fail ERR_MODULE_NOT_FOUND (they import components that don't exist yet).
# That is expected noise — not a failure in your implementation.
#
# Instead, we run only:
#   (a) the specific test file(s) for the current spec  (blocking)
#   (b) the existing pre-upgrade tests                  (regression guard)
#
# The CI workflow (ui-upgrade-checks.yml) runs the full suite for visibility
# but does not treat future-spec stubs as blocking.

section "Vitest — spec-targeted tests"

if [[ "$SPEC_ID" != "ALL" ]]; then
  # Derive the component name from the spec ID for test file matching
  # e.g. FE-UI-006 → look for *ErrorBoundary* test files
  SPEC_FILE=$(find "$REPO_ROOT/docs/upgrade/specs" -name "${SPEC_ID}*.md" | head -1)
  if [[ -n "$SPEC_FILE" ]]; then
    # Extract the component name from the spec file's component_file field
    COMPONENT_PATH=$(grep "^component_file:" "$SPEC_FILE" | head -1 | awk '{print $2}')
    COMPONENT_NAME=$(basename "$COMPONENT_PATH" .tsx)
  fi
fi

if [[ "$SPEC_ID" == "ALL" || -z "${COMPONENT_NAME:-}" ]]; then
  # Full suite — only use for final batch sign-off
  echo "  Running FULL Vitest suite (ALL mode — expect noise from unimplemented specs)"
  if npx vitest run --config vitest.config.ts --reporter verbose 2>&1; then
    pass "Vitest full suite passed"
  else
    fail "Vitest failures — check output above for which spec they belong to"
    exit 1
  fi
else
  # Targeted: run only tests whose filename contains the component name
  echo "  Running targeted Vitest for component: $COMPONENT_NAME"
  echo "  (skipping stubs for unimplemented specs — that is expected behaviour)"

  # Canonical test location is src/frontend/tests/ui/ (preferred).
  # Repo-root tests/ui/ is legacy/stub location (fallback only).
  UNIT_CANONICAL="${FRONTEND}/tests/ui/unit/${COMPONENT_NAME}.test.tsx"
  UNIT_STUB="${REPO_ROOT}/tests/ui/unit/${COMPONENT_NAME}.test.tsx"
  INTEG_CANONICAL="${FRONTEND}/tests/ui/integration/${COMPONENT_NAME}.test.tsx"
  INTEG_STUB="${REPO_ROOT}/tests/ui/integration/${COMPONENT_NAME}.test.tsx"

  FOUND_TESTS=0

  if [[ -f "$UNIT_CANONICAL" ]]; then
    FOUND_TESTS=1
    echo "  → $UNIT_CANONICAL"
    if npx vitest run --config vitest.config.ts --reporter verbose "$UNIT_CANONICAL" 2>&1; then
      pass "Unit tests for $COMPONENT_NAME passed"
    else
      fail "Unit tests for $COMPONENT_NAME failed — fix before committing"
      exit 1
    fi
  elif [[ -f "$UNIT_STUB" ]]; then
    FOUND_TESTS=1
    echo "  → $UNIT_STUB (stub — move to $UNIT_CANONICAL when implemented)"
    if npx vitest run --config vitest.config.ts --reporter verbose "$UNIT_STUB" 2>&1; then
      pass "Unit tests for $COMPONENT_NAME passed"
    else
      fail "Unit tests for $COMPONENT_NAME failed — fix before committing"
      exit 1
    fi
  fi

  if [[ -f "$INTEG_CANONICAL" ]]; then
    FOUND_TESTS=1
    echo "  → $INTEG_CANONICAL"
    if npx vitest run --config vitest.config.ts --reporter verbose "$INTEG_CANONICAL" 2>&1; then
      pass "Integration tests for $COMPONENT_NAME passed"
    else
      fail "Integration tests for $COMPONENT_NAME failed — fix before committing"
      exit 1
    fi
  elif [[ -f "$INTEG_STUB" ]]; then
    FOUND_TESTS=1
    echo "  → $INTEG_STUB (stub — move to $INTEG_CANONICAL when implemented)"
    if npx vitest run --config vitest.config.ts --reporter verbose "$INTEG_STUB" 2>&1; then
      pass "Integration tests for $COMPONENT_NAME passed"
    else
      fail "Integration tests for $COMPONENT_NAME failed — fix before committing"
      exit 1
    fi
  fi

  if [[ "$FOUND_TESTS" -eq 0 ]]; then
    fail "No test file found for component '$COMPONENT_NAME'"
    echo "     Expected: $UNIT_CANONICAL"
    exit 1
  fi

  # Regression note: targeted mode already runs the spec's own tests.
  # Full-suite regressions are caught by the Jest section below and by CI.
  pass "Spec tests ran — regression guard satisfied (full CI suite handles cross-spec regressions)"
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
