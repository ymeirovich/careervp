# Task 9.11: CV Tailoring - Deployment & Verification

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Tasks 9.1-9.10 (All implementation and testing complete)
**Blocking:** None (Final task)

## Overview

Deploy CV tailoring infrastructure to AWS and perform manual verification tests. Validates that the deployed Lambda function, API Gateway route, and DynamoDB table are functional end-to-end with realistic requests.

## Todo

### Deployment Tasks

- [ ] Run `cdk validate` to check CloudFormation syntax
- [ ] Run `cdk synth` to generate CloudFormation template
- [ ] Review `cdk diff` for changes
- [ ] Run `cdk deploy` to deploy infrastructure
- [ ] Verify Lambda function deployed
- [ ] Verify API Gateway route created
- [ ] Verify DynamoDB table created with TTL
- [ ] Verify CloudWatch Logs configured
- [ ] Verify X-Ray tracing enabled

### Manual Verification

- [ ] Test API endpoint with curl (valid request)
- [ ] Test API endpoint with curl (error scenario)
- [ ] Monitor CloudWatch Logs for errors
- [ ] Check X-Ray traces for latency
- [ ] Verify DynamoDB metrics
- [ ] Test with real CV data (if available)
- [ ] Monitor cost (ensure within budget)

### Rollback Procedures

- [ ] Document rollback steps
- [ ] Test rollback if needed
- [ ] Restore to previous version if issues found

### Documentation

- [ ] Document deployment procedure
- [ ] Document API endpoint and authentication
- [ ] Document monitoring and alerting
- [ ] Document troubleshooting guide

### Commit

- [ ] Commit deployment configuration if needed

---

## Deployment Procedure

### Pre-Deployment Checklist

```bash
# 1. Verify all code is committed
git status
# Expected: "working tree clean"

# 2. Run all tests locally
uv run pytest tests/handlers/test_tailoring_handler_unit.py -v
uv run pytest tests/logic/test_tailoring_logic.py -v
uv run pytest tests/cv-tailoring/integration/ -v
uv run pytest tests/cv-tailoring/e2e/ -v

# 3. Verify type checking
uv run mypy src/backend/careervp/handlers/ --strict
uv run mypy src/backend/careervp/logic/ --strict

# 4. Verify code style
uv run ruff format . && uv run ruff check --fix .

# 5. Check for security issues
uv run bandit -r src/backend/careervp/
```

### CloudFormation Validation

```bash
# Validate CloudFormation syntax
cd infra
uv run cdk validate

# Expected output:
# The template is valid.

# Generate CloudFormation template
uv run cdk synth

# Expected output:
# Successfully synthesized to infra/cdk.out/

# Review changes
uv run cdk diff

# Expected output:
# Shows new resources to be created:
# - AWS::Lambda::Function (CVTailoringFunction)
# - AWS::DynamoDB::Table (CVTailoredArtifacts)
# - AWS::ApiGateway::Resource (/api/cv-tailoring)
# - AWS::IAM::Role (Lambda execution role)
# - AWS::CloudWatch::LogGroup (Lambda logs)
# - AWS::Logs::ResourcePolicy (X-Ray write access)
```

### Deployment Commands

```bash
# Deploy to AWS
cd infra
uv run cdk deploy

# When prompted:
# "Do you wish to deploy these changes (y/n)?" → yes

# Expected output:
# CVTailoringStack: creating CloudFormation changeset...
# CVTailoringStack: waiting for changeset to be created...
# CVTailoringStack: waiting for stack create/update to complete...
# CVTailoringStack: done.
# Outputs:
# CVTailoringTableName = cv-tailored-artifacts-xxxxx
# CVTailoringLambdaArn = arn:aws:lambda:...
# CVTailoringApiUrl = https://xxxx.execute-api.us-east-1.amazonaws.com/api/cv-tailoring
```

### Post-Deployment Verification

#### 1. Verify Lambda Function

```bash
# Get Lambda function info
aws lambda get-function --function-name cv-tailoring

# Expected output includes:
# "Runtime": "python3.11"
# "MemorySize": 3072
# "Timeout": 60
# "TracingConfig": {"Mode": "Active"}

# Check Lambda environment variables
aws lambda get-function-configuration --function-name cv-tailoring | grep Environment

# Expected output includes:
# "CV_TAILORING_TABLE_NAME": "cv-tailored-artifacts-..."
# "LOG_LEVEL": "INFO"

# Check recent invocations
aws logs tail /aws/lambda/cv-tailoring --follow
```

#### 2. Verify API Gateway Route

```bash
# Get API Gateway details
aws apigateway get-rest-apis --query 'items[?name==`careervp-api`]'

# Expected output includes API ID

# Get resources
aws apigateway get-resources --rest-api-id <API_ID>

# Expected output includes:
# /api/cv-tailoring resource with POST method

# Get method details
aws apigateway get-method --rest-api-id <API_ID> --resource-id <RESOURCE_ID> --http-method POST

# Expected output includes:
# Integration with Lambda function
```

#### 3. Verify DynamoDB Table

```bash
# Get table description
aws dynamodb describe-table --table-name cv-tailored-artifacts

# Expected output includes:
# "TableStatus": "ACTIVE"
# "BillingModeSummary": {"BillingMode": "PAY_PER_REQUEST"}
# "TimeToLiveDescription": {"AttributeName": "expiration_timestamp", "Enabled": true}
# "GlobalSecondaryIndexes": [{"IndexName": "user_id_created_at_gsi"}]

# Check table metrics (optional, CloudWatch)
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=cv-tailored-artifacts \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

#### 4. Verify CloudWatch Logs

```bash
# Check log group exists
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/cv-tailoring

# Expected output:
# Log group "/aws/lambda/cv-tailoring" with retention policy

# Tail recent logs
aws logs tail /aws/lambda/cv-tailoring --since 1h

# Expected output:
# No errors for successful invocations
```

#### 5. Verify X-Ray Tracing

```bash
# Get service map (might take a few invocations to populate)
aws xray get-service-graph --start-time $(date -u -d '1 hour ago' +%s) --end-time $(date -u +%s)

# Expected output:
# Service graph showing Lambda → DynamoDB connections
```

### Manual API Testing

#### Test 1: Valid Request

```bash
# Get API endpoint from CloudFormation outputs
API_ENDPOINT="https://xxxx.execute-api.us-east-1.amazonaws.com/api/cv-tailoring"

# Create test request
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "application_id": "test_app_456",
    "job_id": "test_job_789",
    "cv_version": 1
  }'

# Expected response:
# HTTP 200
# {
#   "success": true,
#   "code": "CV_TAILORED",
#   "data": {
#     "tailored_cv": {
#       "contact_info": {...},
#       "executive_summary": "...",
#       ...
#     },
#     "metadata": {
#       "application_id": "test_app_456",
#       ...
#     },
#     "token_usage": {
#       "input_tokens": XXXX,
#       "output_tokens": XXXX,
#       ...
#     }
#   }
# }
```

#### Test 2: Missing CV Error

```bash
# Request with non-existent user
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "nonexistent_user",
    "application_id": "test_app_456",
    "job_id": "test_job_789",
    "cv_version": 1
  }'

# Expected response:
# HTTP 400
# {
#   "success": false,
#   "code": "CV_NOT_FOUND",
#   "error": "CV not found"
# }
```

#### Test 3: Invalid JSON

```bash
# Request with invalid JSON
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{invalid json}'

# Expected response:
# HTTP 400
# {
#   "success": false,
#   "code": "VALIDATION_ERROR",
#   "error": "Invalid JSON"
# }
```

#### Test 4: Missing Required Field

```bash
# Request without job_id
curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "application_id": "test_app_456"
  }'

# Expected response:
# HTTP 400
# {
#   "success": false,
#   "code": "VALIDATION_ERROR",
#   "error": "Validation failed: job_id is required"
# }
```

### Performance Testing

```bash
# Measure response time
time curl -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "application_id": "test_app_456",
    "job_id": "test_job_789",
    "cv_version": 1
  }' > /dev/null

# Expected:
# real    0m10s (less than 60s Lambda timeout)
# user    0m0.123s
# sys     0m0.045s
```

### Monitoring Setup

#### CloudWatch Alarms

```bash
# Create error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name cv-tailoring-error-rate \
  --alarm-description "Alert on CV tailoring errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=cv-tailoring

# Create duration alarm
aws cloudwatch put-metric-alarm \
  --alarm-name cv-tailoring-duration \
  --alarm-description "Alert on slow CV tailoring" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --period 300 \
  --threshold 45000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=cv-tailoring
```

#### CloudWatch Dashboard

```bash
# Create dashboard (optional)
aws cloudwatch put-dashboard \
  --dashboard-name cv-tailoring \
  --dashboard-body file://dashboard.json
```

(See `dashboard.json` template below)

### Dashboard Template (dashboard.json)

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Duration", {"stat": "Average"}],
          [".", "Throttles", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Metrics"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", {"stat": "Sum"}],
          [".", "ConsumedReadCapacityUnits", {"stat": "Sum"}],
          [".", "UserErrors", {"stat": "Sum"}],
          [".", "SystemErrors", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "DynamoDB Metrics"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "fields @timestamp, @message, @duration | filter @message like /ERROR/ | stats count() by @message",
        "region": "us-east-1",
        "title": "Error Log Summary"
      }
    }
  ]
}
```

### Rollback Procedure

If issues are discovered:

```bash
# Option 1: Destroy entire stack
cd infra
uv run cdk destroy

# When prompted:
# "Are you sure?" → yes

# Option 2: Revert to previous version (if using Git)
git checkout HEAD~1
cd infra
uv run cdk deploy

# Option 3: Manual rollback (if CDK destroy fails)
aws cloudformation delete-stack --stack-name CVTailoringStack
aws cloudformation wait stack-delete-complete --stack-name CVTailoringStack
```

### Troubleshooting Guide

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Lambda timeout | Check CloudWatch Logs for slow operations | Increase memory (current: 3GB) or check LLM API latency |
| DynamoDB throttling | Check CloudWatch metrics for throttled requests | Table is on-demand, check for scan operations |
| FVS validation failures | Check logs for "hallucinated" errors | Review LLM output and prompt engineering |
| API Gateway 500 | Check Lambda execution role permissions | Verify IAM role has DynamoDB access |
| X-Ray not showing traces | Check if tracing enabled | Verify `TracingConfig: {Mode: Active}` |
| High latency | Check LLM API response time | May be normal for complex requests |
| DynamoDB items not appearing | Check if write succeeded | Verify IAM permissions and table configuration |

### Cost Estimation

```
Monthly costs (estimated):

Lambda:
- 1000 invocations/month × 0.2 ms average = 0.2 GB-seconds
- Free tier: 1M GB-seconds/month
- Cost: $0

DynamoDB (pay-per-request):
- 1000 writes/month × 0.5 KB avg = 500 WCUs
- 1000 reads/month × 0.5 KB avg = 500 RCUs
- Cost: ~$0.25 + storage

API Gateway:
- 1000 requests/month
- Cost: $0.35 (free tier: 1M requests/month)

Total monthly: ~$0.60 (under free tier for small usage)
```

### Documentation

Document the following in a deployment runbook:

1. **API Endpoint**: `<API_ENDPOINT>/api/cv-tailoring`
2. **Authentication**: (As configured in API Gateway)
3. **Request Schema**: See TailorCVRequest model
4. **Response Schema**: See TailorCVResponse model
5. **Error Codes**: See ResultCode constants
6. **Monitoring**: CloudWatch Logs, X-Ray traces, Alarms
7. **Scaling**: Auto-scales with Lambda concurrency limits
8. **SLA**: <5% error rate, <30s p99 latency

---

## Verification Checklist

- [ ] All unit tests passing locally
- [ ] All integration tests passing locally
- [ ] All E2E tests passing locally
- [ ] CloudFormation validates successfully
- [ ] CDK synth completes without errors
- [ ] CDK deploy succeeds
- [ ] Lambda function deployed and active
- [ ] API Gateway route created
- [ ] DynamoDB table created with TTL
- [ ] CloudWatch Logs configured
- [ ] X-Ray tracing enabled
- [ ] Curl test with valid request returns 200
- [ ] Curl test with error scenario returns 400/500
- [ ] CloudWatch Logs show no errors
- [ ] DynamoDB metrics show writes
- [ ] Response times under 60 seconds
- [ ] Alarms configured and monitoring
- [ ] Cost under budget
- [ ] Documentation complete

## Next Steps

After successful deployment:

1. Monitor CloudWatch Logs and Alarms for 24 hours
2. Run load testing (optional)
3. Document any issues found
4. Prepare for Phase 10 (if planned)
5. Archive deployment logs

---

## Notes

- This is a manual verification task (no automated tests in code)
- All AWS commands require appropriate IAM permissions
- Cost estimates are for light usage; adjust for your actual traffic
- Keep deployment logs for debugging and audit purposes
- Consider setting up CloudWatch Alarms for production use
