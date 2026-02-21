#!/bin/bash
# Master Verification Script
# Runs all Phase verification scripts in order

set -e

echo "=============================================="
echo "  REFACTOR2 Master Verification Script"
echo "=============================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Track overall status
OVERALL_ERRORS=0

# Run Phase 0 Exit Verification
echo ""
echo "=============================================="
echo "Running Phase 0 Exit Verification..."
echo "=============================================="
if bash "$SCRIPT_DIR/step_0_exit_verification.sh"; then
    echo "Phase 0: PASSED"
else
    echo "Phase 0: FAILED"
    OVERALL_ERRORS=$((OVERALL_ERRORS + 1))
fi

# Run Phase 1 Exit Verification
echo ""
echo "=============================================="
echo "Running Phase 1 Exit Verification..."
echo "=============================================="
if bash "$SCRIPT_DIR/step_1_exit_verification.sh"; then
    echo "Phase 1: PASSED"
else
    echo "Phase 1: FAILED"
    OVERALL_ERRORS=$((OVERALL_ERRORS + 1))
fi

# Run Auth Migration Verification
echo ""
echo "=============================================="
echo "Running Auth Migration Verification..."
echo "=============================================="
if bash "$SCRIPT_DIR/step_1.1.2_auth_migration_verification.sh"; then
    echo "Auth Migration: PASSED"
else
    echo "Auth Migration: FAILED"
    OVERALL_ERRORS=$((OVERALL_ERRORS + 1))
fi

# Run CORS Verification
echo ""
echo "=============================================="
echo "Running CORS Verification..."
echo "=============================================="
if bash "$SCRIPT_DIR/step_1.5_cors_verification.sh"; then
    echo "CORS: PASSED"
else
    echo "CORS: FAILED"
    OVERALL_ERRORS=$((OVERALL_ERRORS + 1))
fi

# Summary
echo ""
echo "=============================================="
if [ $OVERALL_ERRORS -eq 0 ]; then
    echo "  MASTER VERIFICATION: ALL PASSED"
else
    echo "  MASTER VERIFICATION: $OVERALL_ERRORS PHASES FAILED"
    exit 1
fi
echo "=============================================="
