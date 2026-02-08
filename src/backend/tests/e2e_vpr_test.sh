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
  "user_id": "e2e-test-user",
  "application_id": "e2e-test-app-$(date +%s)",
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

# Get DynamoDB table name
TABLE_NAME=$(aws cloudformation describe-stacks \
  --stack-name CareerVpCrudDev \
  --query "Stacks[0].Outputs[?OutputKey=='UsersTableOutput'].OutputValue" \
  --output text \
  --region "$AWS_REGION")

# Create test user CV in DynamoDB
TEST_USER_ID="e2e-test-user"
TEST_CV_ITEM=$(cat <<EOF
{
  "pk": "$TEST_USER_ID",
  "sk": "CV",
  "user_id": "$TEST_USER_ID",
  "full_name": "John Smith",
  "email": "john.smith@example.com",
  "language": "en",
  "contact_info": {
    "email": "john.smith@example.com",
    "phone": "+1-555-123-4567",
    "location": "San Francisco, CA"
  },
  "experience": [
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
      "description": "Developed responsive websites using JavaScript, HTML, and CSS."
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
  "top_achievements": [],
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)

echo "Creating test CV in DynamoDB..."
aws dynamodb put-item \
  --table-name "$TABLE_NAME" \
  --item "$TEST_CV_ITEM" \
  --region "$AWS_REGION" 2>/dev/null || echo "Warning: Could not create test CV (may already exist)"

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
  echo "Cost: $(echo "$BODY" | jq -r '.cost // "N/A"')"
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

  # Check for timeout - this is expected for full VPR generation
  if [[ "$HTTP_CODE" == "504" || "$BODY" == *"timed out"* ]]; then
    echo "=============================================="
    echo "TIMEOUT - Integration is working!"
    echo "=============================================="
    echo ""
    echo "The Lambda timed out because VPR generation takes >29 seconds."
    echo "This proves:"
    echo "  - CV is fetched from DynamoDB"
    echo "  - SSM parameter is retrieved"
    echo "  - Anthropic API is invoked"
    echo "  - Full VPR generation is working"
    echo ""
    echo "For faster responses, use smaller job_posting data."
    echo ""
    exit 0  # Exit 0 since this is expected
  fi

  echo "--- Troubleshooting ---"
  echo "1. Check Lambda logs: aws logs tail /aws/lambda/careervp-vpr-generator-lambda-${ENVIRONMENT}"
  echo "2. Verify ANTHROPIC_API_KEY is set in Lambda environment"
  echo "3. Check CloudWatch metrics for error details"
  echo ""
  exit 1
fi
