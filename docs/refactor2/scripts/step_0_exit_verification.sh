#!/bin/bash
# Phase 0 Exit Verification Script
# Verifies all Phase 0 security pre-requisites are complete

set -e

echo "=== Phase 0 Exit Verification ==="

cd /Users/yitzchak/Documents/dev/careervp

ERRORS=0

# Test 1: Python dependency audit
echo ""
echo "[1/7] Running Python dependency audit..."
cd src/backend
if uvx --python 3.13 pip-audit -r lambda_requirements.txt 2>&1 | grep -Eq "No known vulnerabilities found|Found 0 vulnerabilities"; then
    echo "PASS: Python dependencies - 0 vulnerabilities"
else
    echo "FAIL: Python dependencies - vulnerabilities found"
    ERRORS=$((ERRORS + 1))
fi
cd ../..

# Test 2: Node dependency audit
echo ""
echo "[2/7] Running Node dependency audit..."
if npm audit --omit=dev --audit-level=high 2>&1 | grep -q "found 0 vulnerabilities"; then
    echo "PASS: Node dependencies - 0 high/critical"
else
    echo "FAIL: Node dependencies - high/critical vulnerabilities found"
    ERRORS=$((ERRORS + 1))
fi

# Test 3: JWT_PRIVATE_KEY/JWT_PUBLIC_KEY in CDK
echo ""
echo "[3/7] Checking JWT env vars in CDK..."
if grep -q "JWT_PRIVATE_KEY" infra/careervp/api_construct.py && \
   grep -q "JWT_PUBLIC_KEY" infra/careervp/api_construct.py; then
    echo "PASS: JWT keys in CDK environment"
else
    echo "FAIL: JWT keys not found in CDK"
    ERRORS=$((ERRORS + 1))
fi

# Test 4: No AUTHORIZER_DISABLED in handlers
echo ""
echo "[4/7] Checking for AUTHORIZER_DISABLED..."
if grep -r "AUTHORIZER_DISABLED" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: AUTHORIZER_DISABLED still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No AUTHORIZER_DISABLED in handlers"
fi

# Test 5: No log_event=True in handlers
echo ""
echo "[5/7] Checking for log_event=True..."
if grep -r "log_event.*True" src/backend/careervp/handlers/ --include="*.py" 2>/dev/null | grep -v "__pycache__" | grep -q .; then
    echo "FAIL: log_event=True still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No log_event=True in handlers"
fi

# Test 6: SSRF validation in web_scraper.py
echo ""
echo "[6/7] Checking SSRF protection..."
if grep -q "_is_safe_url" src/backend/careervp/logic/utils/web_scraper.py 2>/dev/null || \
   grep -q "is_private" src/backend/careervp/logic/utils/web_scraper.py 2>/dev/null; then
    echo "PASS: SSRF validation found"
else
    echo "FAIL: SSRF validation not found"
    ERRORS=$((ERRORS + 1))
fi

# Test 7: Auth check in company_research POST
echo ""
echo "[7/7] Checking company_research auth..."
if grep -q "_extract_authenticated_user_id" src/backend/careervp/handlers/company_research_handler.py 2>/dev/null; then
    echo "PASS: Auth check in company_research"
else
    echo "FAIL: Auth check not found in company_research"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo "PHASE 0 VERIFICATION: PASSED"
    echo "All security pre-requisites complete!"
else
    echo "PHASE 0 VERIFICATION: FAILED"
    echo "$ERRORS checks failed - review above"
    exit 1
fi
echo "==================================="

echo "Phase 0 Exit Criteria:"
echo "[ ] pip-audit reports 0 vulnerabilities"
echo "[ ] npm audit reports 0 high/critical"
echo "[ ] JWT_PRIVATE_KEY/JWT_PUBLIC_KEY in infra env vars"
echo "[ ] No AUTHORIZER_DISABLED in handlers"
echo "[ ] No log_event=True in handlers"
echo "[ ] SSRF validation in web_scraper.py"
echo "[ ] Auth check in company_research POST"

echo ""
echo "=== Phase 0 Exit Verification Complete ==="
