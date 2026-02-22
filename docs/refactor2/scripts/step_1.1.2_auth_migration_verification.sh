#!/bin/bash
# Step 1.1.2: Verify phased auth migration completion
# Focus on true spoofing risks and no-regression checks

set -e

echo "=== Step 1.1.2: Auth Migration Verification ==="

cd /Users/yitzchak/Documents/dev/careervp

ERRORS=0

# Test 1: knowledge_base should not source user identity from query/body payload fields
echo ""
echo "[1/5] Checking knowledge_base identity sourcing..."
if rg -n "params\\.get\\('user_id'\\)|payload\\['user_id'\\]" src/backend/careervp/handlers/knowledge_base_handler.py >/dev/null 2>&1; then
    echo "FAIL: knowledge_base_handler still sources user_id from request input"
    rg -n "params\\.get\\('user_id'\\)|payload\\['user_id'\\]" src/backend/careervp/handlers/knowledge_base_handler.py
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: knowledge_base identity sourced from auth context"
fi

# Test 2: gap handler should not fallback to payload user_id
echo ""
echo "[2/5] Checking gap handler payload fallback..."
if rg -n "_coerce_str\\(payload\\.get\\('user_id'\\)\\)" src/backend/careervp/handlers/gap_handler.py >/dev/null 2>&1; then
    echo "FAIL: gap_handler still falls back to payload user_id"
    rg -n "_coerce_str\\(payload\\.get\\('user_id'\\)\\)" src/backend/careervp/handlers/gap_handler.py
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: gap handler no longer trusts payload user_id"
fi

# Test 3: no AUTHORIZER_DISABLED usage in handlers
echo ""
echo "[3/5] Checking for AUTHORIZER_DISABLED..."
if rg -n "AUTHORIZER_DISABLED" src/backend/careervp/handlers --glob "*.py" >/dev/null 2>&1; then
    echo "FAIL: AUTHORIZER_DISABLED still present"
    rg -n "AUTHORIZER_DISABLED" src/backend/careervp/handlers --glob "*.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No AUTHORIZER_DISABLED in handlers"
fi

# Test 4: x-user-id usage constrained to auth_utils + gated cv_upload fallback
echo ""
echo "[4/5] Checking x-user-id usage..."
if rg -n "x-user-id|X-User-Id" src/backend/careervp/handlers --glob "*.py" | rg -v "auth_utils.py|cv_upload_handler.py" >/dev/null 2>&1; then
    echo "FAIL: x-user-id appears outside auth_utils/cv_upload_handler"
    rg -n "x-user-id|X-User-Id" src/backend/careervp/handlers --glob "*.py" | rg -v "auth_utils.py|cv_upload_handler.py"
    ERRORS=$((ERRORS + 1))
elif ! rg -n "os\\.getenv\\('ENV'" src/backend/careervp/handlers/cv_upload_handler.py >/dev/null 2>&1; then
    echo "FAIL: cv_upload_handler missing ENV=local gate for x-user-id fallback"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: x-user-id usage is constrained and locally gated"
fi

# Test 5: remove dead inline auth helper functions from migrated handlers
echo ""
echo "[5/5] Checking dead inline auth helpers..."
if rg -n "_authorizer_disabled|_extract_user_id_from_authorizer|_extract_claim_user_id|_get_header_case_insensitive|_get_user_id_from_unprotected_request" \
    src/backend/careervp/handlers/cover_letter_handler.py \
    src/backend/careervp/handlers/interview_prep_handler.py \
    src/backend/careervp/handlers/company_research_handler.py \
    src/backend/careervp/handlers/cv_tailoring_handler.py >/dev/null 2>&1; then
    echo "FAIL: Dead inline auth helpers still present in migrated handlers"
    rg -n "_authorizer_disabled|_extract_user_id_from_authorizer|_extract_claim_user_id|_get_header_case_insensitive|_get_user_id_from_unprotected_request" \
        src/backend/careervp/handlers/cover_letter_handler.py \
        src/backend/careervp/handlers/interview_prep_handler.py \
        src/backend/careervp/handlers/company_research_handler.py \
        src/backend/careervp/handlers/cv_tailoring_handler.py
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No dead inline auth helpers in migrated handlers"
fi

# Summary
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo "AUTH MIGRATION: PASSED"
    echo "Phased migration checks succeeded"
else
    echo "AUTH MIGRATION: FAILED"
    echo "$ERRORS issues found"
    exit 1
fi
echo "==================================="

echo ""
echo "=== Step 1.1.2 Verification Complete ==="
