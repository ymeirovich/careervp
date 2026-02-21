#!/bin/bash
# Step 1.5.3: CORS Verification Script
# Verifies CORS is properly configured with allowlist

set -e

echo "=== Step 1.5.3: CORS Verification ==="

cd /Users/yitzchak/Documents/dev/careervp

ERRORS=0

# Test 1: No wildcard CORS
echo ""
echo "[1/3] Checking for wildcard CORS..."
if grep -r "Access-Control-Allow-Origin.*\*" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: Wildcard CORS found:"
    grep -r "Access-Control-Allow-Origin.*\*" src/backend/careervp/handlers/ --include="*.py" | grep -v "__pycache__"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No wildcard CORS in handlers"
fi

# Test 2: CORS utility exists
echo ""
echo "[2/3] Checking for CORS utility..."
if [ -f "src/backend/careervp/handlers/cors_utils.py" ]; then
    echo "PASS: cors_utils.py exists"

    # Verify it has proper validation
    if grep -q "ALLOWED_ORIGINS" src/backend/careervp/handlers/cors_utils.py; then
        echo "PASS: CORS utility has ALLOWED_ORIGINS"
    else
        echo "FAIL: CORS utility missing ALLOWED_ORIGINS"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "FAIL: cors_utils.py not found"
    ERRORS=$((ERRORS + 1))
fi

# Test 3: ALLOWED_ORIGINS in CDK
echo ""
echo "[3/3] Checking ALLOWED_ORIGINS in CDK..."
if grep -q "ALLOWED_ORIGINS" infra/careervp/api_construct.py; then
    echo "PASS: ALLOWED_ORIGINS defined in CDK"
else
    echo "FAIL: ALLOWED_ORIGINS not found in CDK"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo "CORS VERIFICATION: PASSED"
    echo "CORS properly configured!"
else
    echo "CORS VERIFICATION: FAILED"
    echo "$ERRORS issues found"
    exit 1
fi
echo "==================================="

echo ""
echo "=== Step 1.5.3 Verification Complete ==="
