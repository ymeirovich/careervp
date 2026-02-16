#!/usr/bin/env bash
# CareerVP E2E test aligned with OpenAPI + Phase 10 runbook contract.
# Usage:
#   CAREERVP_TOKEN=<jwt> bash tests/e2e/test_sysaid_e2e.sh

set -euo pipefail

API_URL="${CAREERVP_API_BASE_URL:-https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod}"
TOKEN="${CAREERVP_TOKEN:-}"
TIMESTAMP=$(date +%s)

if [ -z "${TOKEN}" ]; then
  echo "ERROR: CAREERVP_TOKEN is required for authenticated endpoints"
  exit 1
fi

echo "=== CareerVP OpenAPI E2E Test ==="
echo "API: ${API_URL}"

auth_header=( -H "Authorization: Bearer ${TOKEN}" )

# -----------------------------------------------------------------------------
# Step 1: Upload CV (POST /users/me/cv)
# -----------------------------------------------------------------------------
echo "=== Step 1: Upload CV ==="
CV_BASE64=$(base64 -i docs/features/02_Yitzchak_Meirovich_Learning_Experience_Specialist_SysAid.docx)
CV_PAYLOAD=$(cat <<JSON
{
  "cv_content": "${CV_BASE64}",
  "file_name": "sysaid_resume.docx"
}
JSON
)

CV_RESPONSE=$(curl -s -X POST "${API_URL}/users/me/cv" \
  "${auth_header[@]}" \
  -H "Content-Type: application/json" \
  -d "${CV_PAYLOAD}")

echo "$CV_RESPONSE" | jq .
CV_ID=$(echo "$CV_RESPONSE" | jq -r '.cv_id // .data.cv_id // empty')

if [ -z "${CV_ID}" ]; then
  echo "ERROR: No cv_id returned from /users/me/cv"
  exit 1
fi

# -----------------------------------------------------------------------------
# Step 2: Create Job (POST /jobs)
# -----------------------------------------------------------------------------
echo "=== Step 2: Create Job ==="
JOB_PAYLOAD=$(cat <<JSON
{
  "title": "Learning Experience Specialist",
  "company_name": "SysAid",
  "description": "Build and launch the SysAid Customer Academy.",
  "url": "https://sysaid.com/careers"
}
JSON
)

JOB_RESPONSE=$(curl -s -X POST "${API_URL}/jobs" \
  "${auth_header[@]}" \
  -H "Content-Type: application/json" \
  -d "${JOB_PAYLOAD}")

echo "$JOB_RESPONSE" | jq .
JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.id // .job_id // .data.id // empty')

if [ -z "${JOB_ID}" ]; then
  echo "ERROR: No job_id returned from /jobs"
  exit 1
fi

# -----------------------------------------------------------------------------
# Step 3: Submit VPR (POST /vpr/generate)
# -----------------------------------------------------------------------------
echo "=== Step 3: Submit VPR ==="
VPR_PAYLOAD=$(cat <<JSON
{
  "cv_id": "${CV_ID}",
  "job_id": "${JOB_ID}",
  "gap_response_ids": [],
  "options": {
    "include_company_research": true,
    "tone": "professional"
  }
}
JSON
)

VPR_RESPONSE=$(curl -s -X POST "${API_URL}/vpr/generate" \
  "${auth_header[@]}" \
  -H "Content-Type: application/json" \
  -d "${VPR_PAYLOAD}")

echo "$VPR_RESPONSE" | jq .
REQUEST_ID=$(echo "$VPR_RESPONSE" | jq -r '.request_id // .id // .job_id // empty')

if [ -z "${REQUEST_ID}" ]; then
  echo "ERROR: No request_id returned from /vpr/generate"
  exit 1
fi

# -----------------------------------------------------------------------------
# Step 4: Poll VPR status (GET /vpr/{vprId})
# -----------------------------------------------------------------------------
echo "=== Step 4: Poll VPR Status ==="
for i in {1..30}; do
  STATUS_RESP=$(curl -s -X GET "${API_URL}/vpr/${REQUEST_ID}" "${auth_header[@]}")
  STATUS=$(echo "$STATUS_RESP" | jq -r '.status // "unknown"')

  echo "Attempt $i/30 -> status=${STATUS}"

  case "$STATUS" in
    completed)
      echo "=== VPR Completed ==="
      echo "$STATUS_RESP" | jq .
      exit 0
      ;;
    failed)
      echo "=== VPR Failed ==="
      echo "$STATUS_RESP" | jq .
      exit 1
      ;;
    pending|processing)
      sleep 10
      ;;
    *)
      sleep 5
      ;;
  esac
done

echo "Timeout waiting for VPR completion"
curl -s -X GET "${API_URL}/vpr/${REQUEST_ID}" "${auth_header[@]}" | jq .
exit 1
