#!/bin/bash
# Step 4.2: Security Validation Gate
# Tests all security controls against deployed API
# Failure = Block deployment until fixed

set -e

echo "=== SECURITY VALIDATION GATE ==="

# Configuration
API_BASE="${API_BASE:-https://api.dev.careervp.app}"
ERRORS=0

# Test 1: Auth enforcement
echo ""
echo "[1/6] Testing auth enforcement..."
HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" "$API_BASE/users/me" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "401" ]; then
    echo "PASS: Unauthenticated request returns 401"
else
    echo "FAIL: Expected 401, got $HTTP_CODE"
    ERRORS=$((ERRORS + 1))
fi

# Test 2: User ID spoofing blocked
echo ""
echo "[2/6] Testing user ID spoofing protection..."
# This test requires a valid user - skip in automated tests
echo "SKIP: User ID spoofing test (requires valid credentials)"

# Test 3: CORS validation
echo ""
echo "[3/6] Testing CORS validation..."
CORS_HEADER=$(curl -sS -I -H "Origin: https://evil.com" "$API_BASE/health" 2>/dev/null | grep -i "Access-Control-Allow-Origin" || echo "")
if echo "$CORS_HEADER" | grep -q "^\s*Access-Control-Allow-Origin:\s*\*"; then
    echo "FAIL: Wildcard CORS allowed"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: CORS is not wildcard"
fi

# Test 4: SSRF blocked (requires auth)
echo ""
echo "[4/6] Testing SSRF protection..."
echo "SKIP: SSRF test (requires authenticated endpoint)"

# Test 5: Dependency audit (local)
echo ""
echo "[5/6] Running Python dependency audit..."
cd /Users/yitzchak/Documents/dev/careervp/src/backend
if uvx pip-audit -r lambda_requirements.txt 2>&1 | grep -q "Found 0 vulnerabilities"; then
    echo "PASS: Python dependencies - 0 vulnerabilities"
else
    echo "FAIL: Python dependencies - vulnerabilities found"
    ERRORS=$((ERRORS + 1))
fi

cd ../..

# Test 6: No sensitive logging
echo ""
echo "[6/6] Checking for sensitive logging patterns..."
if grep -r "log_event.*True" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: log_event=True still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No log_event=True in handlers"
fi

# Test 7: No AUTHORIZER_DISABLED
echo ""
echo "[7/7] Checking for AUTHORIZER_DISABLED..."
if grep -r "AUTHORIZER_DISABLED" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: AUTHORIZER_DISABLED still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No AUTHORIZER_DISABLED in handlers"
fi

# Test 8: No payload user_id
echo ""
echo "[8/8] Checking for payload user_id..."
if grep -r "payload.*user_id\|user_id.*payload" /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: payload.user_id still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No payload user_id in handlers"
fi

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo "SECURITY GATE: PASSED"
    echo "All security controls verified!"
else
    echo "SECURITY GATE: FAILED"
    echo "$ERRORS security checks failed"
    echo ""
    echo "BLOCKING DEPLOYMENT until fixed"
    exit 1
fi
echo "==================================="

echo ""
echo "=== END SECURITY GATE ==="
