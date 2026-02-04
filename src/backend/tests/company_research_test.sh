#!/usr/bin/env bash
set -euo pipefail

# Company Research Integration Test
# Tests the /api/company-research endpoint against deployed infrastructure

API_URL=$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudDev \
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text --region us-east-1)

# Test payload for SysAid
COMPANY_PAYLOAD=$(cat <<'EOF'
{
  "company_name": "SysAid",
  "domain": "www.sysaid.com",
  "job_posting_url": "https://www.sysaid.com/hp-26",
  "job_title": "Senior Software Engineer"
}
EOF
)

echo "=============================================="
echo "Company Research Integration Test"
echo "=============================================="
echo ""
echo "Target API: ${API_URL}api/company-research"
echo "Company: SysAid"
echo ""

# Execute the test
echo "Sending request..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "${API_URL}api/company-research" \
  -H "Content-Type: application/json" \
  -d "$COMPANY_PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

echo ""
echo "Response Code: $HTTP_CODE"
echo ""

# Validate response
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "FAILED: Expected HTTP 200, got $HTTP_CODE"
  echo ""
  echo "Response body:"
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
  exit 1
fi

# Check required fields
echo "Validating response structure..."
ERRORS=0

# Check company_name
COMPANY_NAME=$(echo "$BODY" | jq -r '.company_name' 2>/dev/null || echo "")
if [[ -z "$COMPANY_NAME" || "$COMPANY_NAME" == "null" ]]; then
  echo "  ERROR: Missing or null 'company_name' field"
  ERRORS=$((ERRORS + 1))
else
  echo "  OK: company_name = $COMPANY_NAME"
fi

# Check overview
OVERVIEW=$(echo "$BODY" | jq -r '.overview' 2>/dev/null || echo "")
if [[ -z "$OVERVIEW" || "$OVERVIEW" == "null" ]]; then
  echo "  ERROR: Missing or null 'overview' field"
  ERRORS=$((ERRORS + 1))
elif [[ ${#OVERVIEW} -lt 50 ]]; then
  echo "  ERROR: 'overview' too short (${#OVERVIEW} chars)"
  ERRORS=$((ERRORS + 1))
else
  echo "  OK: overview = ${#OVERVIEW} chars"
fi

# Check values array
VALUES_COUNT=$(echo "$BODY" | jq -r '.values | length' 2>/dev/null || echo "0")
if [[ "$VALUES_COUNT" -lt 2 ]]; then
  echo "  ERROR: 'values' array has fewer than 2 items ($VALUES_COUNT)"
  ERRORS=$((ERRORS + 1))
else
  echo "  OK: values = $VALUES_COUNT items"
fi

# Check source field
SOURCE=$(echo "$BODY" | jq -r '.source' 2>/dev/null || echo "")
if [[ -z "$SOURCE" || "$SOURCE" == "null" ]]; then
  echo "  ERROR: Missing or null 'source' field"
  ERRORS=$((ERRORS + 1))
else
  echo "  OK: source = $SOURCE"
fi

# Check confidence_score
CONFIDENCE=$(echo "$BODY" | jq -r '.confidence_score' 2>/dev/null || echo "")
if [[ -z "$CONFIDENCE" || "$CONFIDENCE" == "null" ]]; then
  echo "  ERROR: Missing or null 'confidence_score' field"
  ERRORS=$((ERRORS + 1))
elif [[ "$CONFIDENCE" == "0" ]]; then
  echo "  WARNING: confidence_score is 0 - research may have failed silently"
else
  echo "  OK: confidence_score = $CONFIDENCE"
fi

echo ""
echo "=============================================="
echo "Test Summary"
echo "=============================================="

if [[ $ERRORS -gt 0 ]]; then
  echo "FAILED: $ERRORS validation error(s) found"
  echo ""
  echo "Full response:"
  echo "$BODY" | jq .
  exit 1
else
  echo "SUCCESS: All validations passed"
  echo ""
  echo "Company: $(echo "$BODY" | jq -r '.company_name')"
  echo "Source: $(echo "$BODY" | jq -r '.source')"
  echo "Confidence: $(echo "$BODY" | jq -r '.confidence_score')"
  echo "Values: $(echo "$BODY" | jq -r '.values | join(", ")')"
  echo ""
  echo "Full response:"
  echo "$BODY" | jq .
  exit 0
fi
