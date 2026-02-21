#!/bin/bash
# Step 1.1.2: Verify All Handlers Migrated to Standardized Auth
# Verifies auth migration completion

set -e

echo "=== Step 1.1.2: Auth Migration Verification ==="

cd /Users/yitzchak/Documents/dev/careervp

ERRORS=0

# Test 1: No payload user_id
echo ""
echo "[1/3] Checking for payload user_id..."
if grep -r "payload.*user_id\|user_id.*payload" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: payload.user_id still present:"
    grep -r "payload.*user_id\|user_id.*payload" src/backend/careervp/handlers/ --include="*.py" | grep -v "__pycache__"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No payload user_id in handlers"
fi

# Test 2: No AUTHORIZER_DISABLED
echo ""
echo "[2/3] Checking for AUTHORIZER_DISABLED..."
if grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: AUTHORIZER_DISABLED still present:"
    grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/ --include="*.py" | grep -v "__pycache__"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No AUTHORIZER_DISABLED in handlers"
fi

# Test 3: No direct authorizer extraction (except in auth_utils.py)
echo ""
echo "[3/3] Checking for direct authorizer extraction..."
if grep -r "requestContext.*authorizer" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -v "auth_utils.py" | grep -q .; then
    echo "FAIL: Direct authorizer extraction found (except in auth_utils.py):"
    grep -r "requestContext.*authorizer" src/backend/careervp/handlers/ --include="*.py" | grep -v "__pycache__" | grep -v "auth_utils.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No direct authorizer extraction"
fi

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo "AUTH MIGRATION: PASSED"
    echo "All handlers migrated to standardized auth!"
else
    echo "AUTH MIGRATION: FAILED"
    echo "$ERRORS issues found"
    exit 1
fi
echo "==================================="

echo ""
echo "=== Step 1.1.2 Verification Complete ==="
