# CV Tailoring E2E Test Suite

## Overview

This directory contains an end-to-end (E2E) test suite for verifying the CV Tailoring feature deployed on AWS.

## Files

| File | Description |
|------|-------------|
| `cv_tailoring_e2e_test.py` | Main E2E test script |
| `cv_tailoring_e2e_results.json` | Test results (generated) |
| `Sysaid Job Description.txt` | Sample job description for testing |
| `Job Post Example 1.md` | Alternative job posting example |

## Quick Start

### 1. Deploy to AWS

```bash
cd src/backend
make deploy
```

### 2. Run E2E Tests

```bash
# From the artifacts directory
cd docs/features/artifacts

# Option A: Let script detect API URL from CloudFormation
python cv_tailoring_e2e_test.py

# Option B: Specify API URL explicitly
python cv_tailoring_e2e_test.py --api-url https://your-api-id.execute-api.us-east-1.amazonaws.com/prod

# Option C: With environment variables
export API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
export CV_ID=your-test-cv-id
export USER_ID=your-test-user-id
python cv_tailoring_e2e_test.py
```

## Test Cases

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `cv_upload` | Upload a CV via /api/cv | 200 with parsed CV |
| `cv_tailoring_basic` | Basic CV tailoring request | 200 with tailored CV |
| `cv_tailoring_with_preferences` | CV tailoring with custom preferences | 200 with tailored CV |
| `invalid_cv_id` | Request CV for non-existent user | 400 Bad Request |
| `validation_error` | Submit invalid job description | 400 Bad Request |

## Sample Output

```text
============================================================
CV Tailoring E2E Test Suite
============================================================
API URL: https://abc123.execute-api.us-east-1.amazonaws.com/prod
Test CV ID: test-cv-001
User ID: test-user-001
Timestamp: 2024-01-15T10:30:00.000Z
============================================================

Test: Health Check
  URL: https://.../api/cv-tailoring/health
  Status: 404
  Note: Health endpoint not implemented or not available
  Result: PASSED

Test: Invalid CV ID
  URL: https://.../api/cv-tailoring
  CV ID: non-existent-cv
  Status: 404
  Correct: Returns 404 for non-existent CV
  Result: PASSED

Test: CV Tailoring Endpoint
  URL: https://.../api/cv-tailoring
  CV ID: test-cv-001
  Status: 200
  Success: True
  Tailored CV received: Yes
  Tailored Summary: Senior Python Developer with 8 years of experience...
  Result: PASSED

============================================================
Test Summary
============================================================
Total: 5
Passed: 5
Failed: 0
Success Rate: 100.0%
```

## CI/CD Integration

### GitHub Actions

Add this to your workflow:

```yaml
e2e-test:
  runs-on: ubuntu-latest
  needs: deploy
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.14"
    - name: Install dependencies
      run: pip install requests boto3
    - name: Run E2E tests
      run: |
        cd docs/features/artifacts
        python cv_tailoring_e2e_test.py \
          --api-url ${{ env.API_URL }} \
          --cv-id ${{ env.CV_ID }} \
          --user-id ${{ env.USER_ID }}
```

## Troubleshooting

### Connection Refused

If tests fail with connection errors:
1. Verify the API is deployed: `aws cloudformation describe-stacks --stack-name CareerVpCrudDev`
2. Check the API URL in CloudFormation outputs
3. Verify security groups allow outbound HTTPS

### 401 Unauthorized

Ensure authentication is configured:
1. Check API Gateway authorizer is working
2. Verify Cognito or JWT tokens if required

### 500 Server Error

Check CloudWatch logs:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/cv-tailoring-handler \
  --start-time $(date -d '10 minutes ago' +%s)000
```

## Test Data

### Sample CV Structure

The test uses a sample CV with the following structure:
- Personal info (name, email, phone, location)
- Professional summary
- Work experience (2 positions)
- Education (1 degree)
- Skills (6 skills with levels)
- Certifications (1 AWS cert)
- Languages (English, Hebrew)

### Sample Job Description

A 300+ word job description for a Senior Python Developer role focusing on:
- Python/AWS expertise
- Cloud infrastructure
- Containerization (Docker, Kubernetes)
- Microservices architecture
