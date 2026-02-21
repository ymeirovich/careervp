#!/bin/bash
# Phase 1 Exit Verification Script
# Verifies all Phase 1 critical fixes are complete

set -e

echo "=== Phase 1 Exit Verification ==="

cd /Users/yitzchak/Documents/dev/careervp

ERRORS=0

# Test 1: Run all unit tests
echo ""
echo "[1/8] Running unit tests..."
cd src/backend
if uv run pytest tests/unit/ -v --tb=short 2>&1; then
    echo "PASS: All unit tests pass"
else
    echo "FAIL: Unit tests failed"
    ERRORS=$((ERRORS + 1))
fi
cd ../..

# Test 2: No AUTHORIZER_DISABLED in handlers
echo ""
echo "[2/8] Checking for AUTHORIZER_DISABLED..."
if grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: AUTHORIZER_DISABLED still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No AUTHORIZER_DISABLED in handlers"
fi

# Test 3: No log_event=True in handlers
echo ""
echo "[3/8] Checking for log_event=True..."
if grep -r "log_event.*True" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: log_event=True still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No log_event=True in handlers"
fi

# Test 4: No payload.user_id in handlers
echo ""
echo "[4/8] Checking for payload user_id..."
if grep -r "payload.*user_id\|user_id.*payload" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: payload.user_id still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No payload user_id in handlers"
fi

# Test 5: CORS uses allowlist, not wildcard
echo ""
echo "[5/8] Checking CORS configuration..."
if grep -r "Access-Control-Allow-Origin.*\*" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: Wildcard CORS still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: CORS uses allowlist, not wildcard"
fi

# Test 6: auth_utils.py exists
echo ""
echo "[6/8] Checking auth_utils.py..."
if [ -f "src/backend/careervp/handlers/auth_utils.py" ]; then
    echo "PASS: auth_utils.py exists"
else
    echo "FAIL: auth_utils.py not found"
    ERRORS=$((ERRORS + 1))
fi

# Test 7: knowledge_base_handler has auth
echo ""
echo "[7/8] Checking knowledge_base_handler auth..."
if grep -q "extract_user_id\|_extract_authenticated_user_id" src/backend/careervp/handlers/knowledge_base_handler.py 2>/dev/null; then
    echo "PASS: knowledge_base_handler has auth"
else
    echo "FAIL: knowledge_base_handler missing auth"
    ERRORS=$((ERRORS + 1))
fi

# Test 8: CORS utility exists
echo ""
echo "[8/8] Checking CORS utility..."
if [ -f "src/backend/careervp/handlers/cors_utils.py" ]; then
    echo "PASS: cors_utils.py exists"
else
    echo "FAIL: cors_utils.py not found"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo "PHASE 1 VERIFICATION: PASSED"
    echo "All critical fixes complete!"
else
    echo "PHASE 1 VERIFICATION: FAILED"
    echo "$ERRORS checks failed - review above"
    exit 1
fi
echo "==================================="

echo ""
echo "=== Phase 1 Exit Verification Complete ==="
