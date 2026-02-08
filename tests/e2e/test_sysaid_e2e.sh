#!/usr/bin/env bash
# CareerVP E2E Test with SysAid CV and Job Description
# Usage: bash test_sysaid_e2e.sh

set -euo pipefail

API_URL="https://05fj149ekg.execute-api.us-east-1.amazonaws.com/prod"
USER_ID="yitzchak-test"
TIMESTAMP=$(date +%s)
APP_ID="sysaid-learning-academy-${TIMESTAMP}"

echo "=== CareerVP E2E Test ==="
echo "API: ${API_URL}"
echo "User: ${USER_ID}"
echo "App ID: ${APP_ID}"
echo ""

# Step 1: Read and upload CV
echo "=== Step 1: Upload CV (DOCX) ==="
CV_BASE64=$(base64 -i docs/features/02_Yitzchak_Meirovich_Learning_Experience_Specialist_SysAid.docx)
CV_PAYLOAD=$(cat <<EOF
{
  "user_id": "${USER_ID}",
  "file_content": "${CV_BASE64}",
  "file_type": "docx"
}
EOF
)

echo "Uploading CV..."
CV_RESPONSE=$(curl -s -X POST "${API_URL}/api/cv" \
  -H "Content-Type: application/json" \
  -d "${CV_PAYLOAD}")

echo "$CV_RESPONSE" | jq .

# Extract CV parsing result
CV_RESULT=$(echo "$CV_RESPONSE" | jq -r '.message // "CV uploaded"')
echo "CV Upload Result: $CV_RESULT"
echo ""

# Step 2: Create VPR Job with SysAid Job Description
echo "=== Step 2: Create VPR Job ==="
VPR_PAYLOAD=$(cat <<EOF
{
  "user_id": "${USER_ID}",
  "application_id": "${APP_ID}",
  "job_posting": {
    "title": "Learning Experience Specialist",
    "company": "SysAid",
    "description": "SysAid is looking for a strategic and creative Learning Experience Specialist to build and launch the SysAid Customer Academy. In this pivotal role, you will be responsible for executing our vision of a unified, scalable learning hub that empowers customers, partners, and internal teams.",
    "requirements": [
      "3+ years of experience in Instructional Design, Learning & Development, or Customer Education in a SaaS environment",
      "Proven experience selecting, implementing, and managing an LMS",
      "Strong proficiency in content creation tools",
      "Experience building certification programs from scratch is a huge plus",
      "Ability to translate complex technical concepts into accessible, engaging learning experiences",
      "Strategic mindset: connect educational initiatives to business KPIs like MRR, adoption, and support ticket reduction"
    ],
    "responsibilities": [
      "Lead LMS setup and deployment for the Customer Academy",
      "Define Academy structure and branding for world-class user experience",
      "Design certification framework for paid and free certification programs",
      "Develop role-based learning tracks for external users (Admins, IT Managers, Service Desk Agents)",
      "Create internal onboarding and enablement paths for Customer Care, Customer Revenue, Sales Engineers",
      "Build specialized readiness certifications for major product releases",
      "Develop gamification through badges and ranks to foster peer-to-peer learning",
      "Create paid certification programs and advanced instructor-led bootcamps for revenue generation"
    ]
  }
}
EOF
)

echo "Creating VPR job..."
RESPONSE=$(curl -s -X POST "${API_URL}/api/vpr" \
  -H "Content-Type: application/json" \
  -d "${VPR_PAYLOAD}")

echo "$RESPONSE" | jq .

JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id // empty')

if [ -z "$JOB_ID" ]; then
  echo "ERROR: No job_id returned"
  exit 1
fi

echo ""
echo "Job ID: $JOB_ID"
echo ""

# Step 3: Poll for Completion
echo "=== Step 3: Poll for Completion ==="
echo "Polling up to 30 times (5 min max)..."
echo ""

for i in {1..30}; do
  echo "Attempt $i/30..."
  STATUS_RESP=$(curl -s "${API_URL}/api/vpr/status/${JOB_ID}")
  STATUS=$(echo "$STATUS_RESP" | jq -r '.status // "UNKNOWN"')

  echo "  Status: $STATUS"

  case "$STATUS" in
    COMPLETED)
      echo ""
      echo "=== VPR Result ==="
      echo "$STATUS_RESP" | jq '.'

      # Download and display result
      RESULT_URL=$(echo "$STATUS_RESP" | jq -r '.result_url // empty')
      if [ -n "$RESULT_URL" ] && [ "$RESULT_URL" != "null" ]; then
        echo ""
        echo "=== Downloading VPR Result ==="
        curl -s "$RESULT_URL" | jq '.' > /tmp/vpr_result.json
        cat /tmp/vpr_result.json | jq '.'
      fi
      exit 0
      ;;
    FAILED)
      echo ""
      echo "=== Job Failed ==="
      echo "$STATUS_RESP" | jq '.error // "Unknown error"'
      exit 1
      ;;
    PROCESSING|PENDING)
      echo "  Waiting 10 seconds..."
      sleep 10
      ;;
    *)
      echo "  Unknown status, waiting 5 seconds..."
      sleep 5
      ;;
  esac
done

echo ""
echo "Timeout waiting for job completion"
echo "Final status check:"
curl -s "${API_URL}/api/vpr/status/${JOB_ID}" | jq '.'
exit 1
