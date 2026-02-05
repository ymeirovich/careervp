# Task 10.11: Deployment

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.10 (E2E Tests)
**Blocking:** None (Final Task)
**Complexity:** Low
**Duration:** 1 hour
**Test File:** N/A (Manual Verification)

## Overview

Deploy cover letter generation feature to dev/staging/prod environments. Includes CDK deployment, environment configuration, and verification steps.

## Todo

### Pre-Deployment Checklist

- [ ] All unit tests passing (146 tests)
- [ ] All integration tests passing (22 tests)
- [ ] All infrastructure tests passing (14 tests)
- [ ] Code coverage > 90%
- [ ] ruff format passes (no changes)
- [ ] ruff check passes (no errors)
- [ ] mypy --strict passes (no errors)
- [ ] CDK synth succeeds

### Deployment Steps

- [ ] Deploy to dev environment
- [ ] Run smoke tests against dev
- [ ] Deploy to staging environment
- [ ] Run E2E tests against staging
- [ ] Deploy to production (with approval)
- [ ] Monitor CloudWatch for errors

### Post-Deployment Verification

- [ ] API endpoint responds with 200
- [ ] Cover letter generation works end-to-end
- [ ] CloudWatch metrics flowing
- [ ] No error alarms triggered
- [ ] Rate limiting working

---

## Codex Implementation Guide

### Pre-Deployment Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run all tests
uv run pytest tests/cover-letter/ -v --tb=short

# Expected output:
# tests/cover-letter/unit/test_validation.py::... PASSED (19 tests)
# tests/cover-letter/unit/test_cover_letter_logic.py::... PASSED (27 tests)
# tests/cover-letter/unit/test_cover_letter_prompt.py::... PASSED (16 tests)
# tests/cover-letter/unit/test_fvs_integration.py::... PASSED (24 tests)
# tests/cover-letter/unit/test_cover_letter_handler_unit.py::... PASSED (19 tests)
# tests/cover-letter/unit/test_cover_letter_dal_unit.py::... PASSED (14 tests)
# tests/cover-letter/unit/test_cover_letter_models.py::... PASSED (27 tests)
# tests/cover-letter/integration/test_cover_letter_handler_integration.py::... PASSED (22 tests)
# tests/cover-letter/infrastructure/test_cover_letter_stack.py::... PASSED (14 tests)
# tests/cover-letter/e2e/test_cover_letter_flow.py::... PASSED/SKIPPED (20 tests)
#
# Total: 202+ tests PASSED

# Check coverage
uv run pytest tests/cover-letter/ --cov=careervp --cov-report=term-missing

# Expected: Coverage > 90%

# Code quality checks
uv run ruff format src/backend/careervp/ --check
uv run ruff check src/backend/careervp/
uv run mypy src/backend/careervp/ --strict

# CDK synth
cd /Users/yitzchak/Documents/dev/careervp
cdk synth --app "python infra/app.py" CareervpStack
```

### Deployment Commands

#### Deploy to Dev

```bash
cd /Users/yitzchak/Documents/dev/careervp

# Set environment
export AWS_PROFILE=careervp-dev
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=us-east-1

# Deploy
cdk deploy --app "python infra/app.py" CareervpStack-Dev \
    --require-approval never \
    --context environment=dev

# Verify deployment
aws cloudformation describe-stacks \
    --stack-name CareervpStack-Dev \
    --query 'Stacks[0].StackStatus'

# Expected: "UPDATE_COMPLETE" or "CREATE_COMPLETE"
```

#### Smoke Test Dev

```bash
# Get API endpoint
API_URL=$(aws cloudformation describe-stacks \
    --stack-name CareervpStack-Dev \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text)

# Test health endpoint
curl -s "${API_URL}/health" | jq .

# Test cover letter endpoint (with auth)
curl -X POST "${API_URL}/api/cover-letter" \
    -H "Authorization: Bearer ${TEST_JWT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "cv_id": "cv_test",
        "job_id": "job_test",
        "company_name": "TestCorp",
        "job_title": "Engineer"
    }' | jq .
```

#### Deploy to Staging

```bash
export AWS_PROFILE=careervp-staging

cdk deploy --app "python infra/app.py" CareervpStack-Staging \
    --require-approval broadening \
    --context environment=staging
```

#### Run E2E Tests Against Staging

```bash
export API_BASE_URL="https://api.staging.careervp.com"
export TEST_JWT_TOKEN="staging_test_token"

cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/cover-letter/e2e/ -v
```

#### Deploy to Production

```bash
export AWS_PROFILE=careervp-prod

# Production deployment requires approval
cdk deploy --app "python infra/app.py" CareervpStack-Prod \
    --require-approval always \
    --context environment=prod

# Wait for manual approval in terminal
```

### Post-Deployment Verification

```bash
# Check Lambda function
aws lambda get-function \
    --function-name careervp-cover-letter-handler \
    --query 'Configuration.{State:State,LastModified:LastModified}'

# Check API Gateway
aws apigateway get-rest-apis \
    --query 'items[?name==`CareerVP-API`].{id:id,name:name}'

# Check CloudWatch metrics (last 5 minutes)
aws cloudwatch get-metric-statistics \
    --namespace CareerVP \
    --metric-name CoverLetterGenerated \
    --start-time $(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum

# Check for errors
aws cloudwatch get-metric-statistics \
    --namespace CareerVP \
    --metric-name CoverLetterError \
    --start-time $(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum

# Check Lambda logs (last 5 minutes)
aws logs filter-log-events \
    --log-group-name /aws/lambda/careervp-cover-letter-handler \
    --start-time $(date -u -v-5M +%s)000 \
    --filter-pattern "ERROR"
```

### Rollback Procedure

If issues are detected after deployment:

```bash
# Get previous version
PREVIOUS_VERSION=$(aws cloudformation describe-stack-events \
    --stack-name CareervpStack-Prod \
    --query 'StackEvents[?ResourceStatus==`UPDATE_COMPLETE`].PhysicalResourceId' \
    --output text | head -2 | tail -1)

# Rollback to previous version
cdk deploy --app "python infra/app.py" CareervpStack-Prod \
    --rollback true

# Or use CloudFormation directly
aws cloudformation rollback-stack \
    --stack-name CareervpStack-Prod
```

### Monitoring Setup

```bash
# Create CloudWatch dashboard (one-time)
aws cloudwatch put-dashboard \
    --dashboard-name CoverLetter-Metrics \
    --dashboard-body file://dashboards/cover-letter-dashboard.json

# Create alarm for high error rate
aws cloudwatch put-metric-alarm \
    --alarm-name CoverLetter-HighErrorRate \
    --metric-name CoverLetterError \
    --namespace CareerVP \
    --statistic Sum \
    --period 60 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789:alerts

# Create alarm for high latency
aws cloudwatch put-metric-alarm \
    --alarm-name CoverLetter-HighLatency \
    --metric-name CoverLetterDuration \
    --namespace CareerVP \
    --statistic p95 \
    --period 300 \
    --threshold 20000 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 3 \
    --alarm-actions arn:aws:sns:us-east-1:123456789:alerts
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All 202+ tests passing
- [ ] Code coverage > 90%
- [ ] No linting errors
- [ ] No type errors
- [ ] CDK synth successful
- [ ] Security review completed (if required)
- [ ] Documentation updated

### Dev Deployment

- [ ] CDK deploy successful
- [ ] Lambda function created/updated
- [ ] API Gateway route added
- [ ] DynamoDB permissions granted
- [ ] Bedrock permissions granted
- [ ] Smoke tests passing

### Staging Deployment

- [ ] CDK deploy successful
- [ ] E2E tests passing
- [ ] Performance acceptable (< 20s p95)
- [ ] No error alarms
- [ ] CloudWatch metrics flowing

### Production Deployment

- [ ] Approval obtained
- [ ] CDK deploy successful
- [ ] Smoke tests passing
- [ ] Monitoring dashboards working
- [ ] Alarms configured
- [ ] Runbook updated
- [ ] On-call notified

### Post-Deployment

- [ ] API endpoint accessible
- [ ] Cover letters generating correctly
- [ ] Quality scores in expected range
- [ ] No elevated error rates
- [ ] Latency within SLA (< 20s p95)

---

## Common Issues & Solutions

### Issue 1: Lambda Timeout
**Symptom:** 504 Gateway Timeout errors
**Solution:** Verify Lambda timeout is 300s, API Gateway timeout is 299s

### Issue 2: Bedrock Permission Denied
**Symptom:** AccessDenied when calling Bedrock
**Solution:** Verify Lambda role has `bedrock:InvokeModel` permission

### Issue 3: DynamoDB Throttling
**Symptom:** ProvisionedThroughputExceeded errors
**Solution:** Switch to PAY_PER_REQUEST billing mode

### Issue 4: High Latency
**Symptom:** p95 latency > 20s
**Solution:** Check for cold starts, consider provisioned concurrency

---

## Success Criteria

Phase 10: Cover Letter Generation is COMPLETE when:

1. ✅ All tests passing (202+ tests)
2. ✅ Deployed to all environments
3. ✅ E2E tests passing in staging
4. ✅ No error alarms in production
5. ✅ Latency within SLA
6. ✅ Documentation complete
7. ✅ Monitoring configured

---

## References

- [COVER_LETTER_DESIGN.md](../../architecture/COVER_LETTER_DESIGN.md) - Architecture
- [COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md) - API specification
- [CDK Documentation](https://docs.aws.amazon.com/cdk/) - CDK reference
- [CareerVP Runbook](../../runbooks/) - Operational procedures
