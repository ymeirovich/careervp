#!/usr/bin/env bash
# CareerVP E2E VPR Generation Test
# Usage: bash src/backend/tests/e2e_vpr_test.sh [env]
# Requires: aws CLI, jq, curl

set -euo pipefail

ENVIRONMENT="${1:-dev}"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. && pwd)"

# Load .env if exists
if [[ -f "${ROOT}/.env" ]]; then
  set -a
  source "${ROOT}/.env"
  set +a
fi

# Get API Gateway URL from CloudFormation
API_URL=$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudDev \
  --query "Stacks[0].Outputs[?OutputKey=='Apigateway'].OutputValue" \
  --output text \
  --region "$AWS_REGION")

if [[ -z "$API_URL" || "$API_URL" == "None" ]]; then
  echo "ERROR: Could not resolve API Gateway URL"
  exit 1
fi

echo "=============================================="
echo "CareerVP E2E VPR Generation Test"
echo "=============================================="
echo "API URL: ${API_URL}"
echo "Environment: ${ENVIRONMENT}"
echo ""

# Complete VPR request payload with valid CV data
VPR_PAYLOAD=$(cat <<'EOF'
{
  "user_id": "e2e-test-user-$(date +%s)",
  "cv": {
    "full_name": "John Smith",
    "email": "john.smith@example.com",
    "phone": "+1-555-123-4567",
    "location": "San Francisco, CA",
    "summary": "Senior software engineer with 8+ years of experience in distributed systems and cloud architecture. Proven track record of building scalable microservices and leading engineering teams.",
    "work_experience": [
      {
        "company": "TechCorp Inc",
        "title": "Senior Software Engineer",
        "start_date": "2021-03",
        "end_date": "Present",
        "description": "Led development of microservices architecture using Python and AWS. Managed a team of 5 engineers. Reduced system latency by 40% through caching optimization."
      },
      {
        "company": "StartupXYZ",
        "title": "Software Engineer",
        "start_date": "2018-06",
        "end_date": "2021-02",
        "description": "Built RESTful APIs using Python Flask and Django. Implemented CI/CD pipelines reducing deployment time by 60%."
      },
      {
        "company": "WebAgency",
        "title": "Junior Developer",
        "start_date": "2016-01",
        "end_date": "2018-05",
        "description": "Developed responsive websites using JavaScript, HTML, and CSS. Collaborated with design team to implement pixel-perfect UIs."
      }
    ],
    "education": [
      {
        "institution": "Stanford University",
        "degree": "Master of Science",
        "field": "Computer Science",
        "graduation_year": 2016
      },
      {
        "institution": "UC Berkeley",
        "degree": "Bachelor of Science",
        "field": "Computer Science",
        "graduation_year": 2014
      }
    ],
    "skills": [
      "Python", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Redis",
      "System Design", "Team Leadership", "CI/CD", "Microservices"
    ],
    "certifications": [
      {
        "name": "AWS Solutions Architect Professional",
        "issuer": "Amazon Web Services",
        "year": 2023
      }
    ],
    "languages": ["English (Native)", "Spanish (Conversational)"]
  },
  "job_posting": {
    "title": "Staff Software Engineer, Platform Infrastructure",
    "company": "CloudScale Tech",
    "description": "We are looking for a Staff Software Engineer to lead our platform infrastructure team. You will be responsible for building and maintaining our cloud-native platform that powers millions of requests per day.\n\nRequirements:\n- 7+ years of experience in software engineering\n- Strong expertise in distributed systems and cloud architecture\n- Experience with Kubernetes and container orchestration\n- Proficiency in Python or Go\n- Experience leading technical teams\n\nNice to have:\n- Experience with Terraform or Infrastructure as Code\n- Background in performance engineering\n- Open source contributions",
    "requirements": [
      "7+ years software engineering experience",
      "Expertise in distributed systems",
      "Cloud architecture experience",
      "Kubernetes experience",
      "Python or Go proficiency",
      "Team leadership experience"
    ],
    "responsibilities": [
      "Design and implement platform infrastructure",
      "Lead technical architecture decisions",
      "Mentor junior engineers",
      "Optimize system performance",
      "Collaborate with cross-functional teams"
    ]
  },
  "language": "en"
}
EOF
)

echo "Sending VPR generation request..."
echo "Payload size: $(echo "$VPR_PAYLOAD" | wc -c) bytes"
echo ""

# Send request and capture response
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "${API_URL}api/vpr" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "$VPR_PAYLOAD")

# Extract HTTP status code (last line)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
# Extract body (all but last line)
BODY=$(echo "$RESPONSE" | sed '$d')

echo "=============================================="
echo "Response Status: $HTTP_CODE"
echo "=============================================="
echo ""

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "SUCCESS! VPR generated successfully."
  echo ""
  echo "--- VPR Response ---"
  echo "$BODY" | jq .
  echo ""
  echo "--- Summary ---"
  echo "Executive Summary:"
  echo "$BODY" | jq -r '.executive_summary // "N/A"' | head -c 500
  echo ""
  echo ""
  echo "Evidence Items: $(echo "$BODY" | jq '.evidence_matrix | length')"
  echo ""
  echo "Token Usage:"
  echo "$BODY" | jq -r '.token_usage | "  Input: \(.input_tokens), Output: \(.output_tokens)"'
  echo ""
  echo "Cost: $(echo "$BODY" | jq -r '.cost // "N/A")"
  echo ""
  echo "=============================================="
  echo "E2E TEST PASSED"
  echo "=============================================="
  exit 0
else
  echo "FAILED with HTTP $HTTP_CODE"
  echo ""
  echo "--- Error Response ---"
  echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
  echo ""
  echo "--- Troubleshooting ---"
  echo "1. Check Lambda logs: aws logs tail /aws/lambda/careervp-vpr-generator-lambda-${ENVIRONMENT}"
  echo "2. Verify ANTHROPIC_API_KEY is set in Lambda environment"
  echo "3. Check CloudWatch metrics for error details"
  echo ""
  exit 1
fi
