# Task 09: Final Verification & Deployment Readiness

## Overview

Final checklist before deploying Gap Analysis to production.

**Dependencies:** All previous tasks (01-08)
**Estimated time:** 2 hours
**Goal:** Ensure production readiness

---

## Pre-Deployment Checklist

### Code Quality

```bash
cd src/backend

# Format all code
uv run ruff format .

# Lint all code
uv run ruff check --fix .

# Type check all code
uv run mypy careervp --strict

# Expected: No errors
```

### Test Coverage

```bash
# Run full test suite
uv run pytest tests/gap-analysis/ -v --tb=short

# Generate coverage report
uv run pytest tests/gap-analysis/ --cov=careervp --cov-report=term-missing --cov-report=html

# Coverage targets:
# - careervp.logic.gap_analysis: ≥95%
# - careervp.handlers.gap_handler: ≥90%
# - careervp.logic.prompts.gap_analysis_prompt: ≥85%
# - careervp.handlers.utils.validation: ≥95%

# Total coverage: ≥90%
```

### Infrastructure

```bash
cd infra

# Synthesize stack
npx cdk synth

# Check diff (if deployed before)
npx cdk diff

# Expected: Only gap-analysis Lambda and route additions
```

---

## Documentation Review

### Verify All Documentation Complete

- [ ] [GAP_ANALYSIS_DESIGN.md](../../architecture/GAP_ANALYSIS_DESIGN.md) - Architecture documented
- [ ] [GAP_SPEC.md](../../specs/gap-analysis/GAP_SPEC.md) - API spec complete
- [ ] [VPR_ASYNC_DESIGN.md](../../architecture/VPR_ASYNC_DESIGN.md) - Foundation documented
- [ ] Task files 01-09 - All implementation guidance complete
- [ ] Code docstrings - All functions documented
- [ ] README.md - Task overview complete

### Update Related Documentation

```bash
# Update main README if needed
# Update CHANGELOG.md
# Update API documentation (Swagger/OpenAPI)
```

---

## Security Review

### Security Checklist

- [ ] File size validation enforced (10MB)
- [ ] Text length validation enforced (1M chars)
- [ ] JWT authentication required
- [ ] User isolation enforced (can't access other users' CVs)
- [ ] User ID from JWT validated against request
- [ ] No SQL injection vectors
- [ ] No XSS vectors
- [ ] No sensitive data in logs
- [ ] Proper error messages (no stack traces to client)
- [ ] CORS configured correctly

### Run Security Tests

```bash
# Check for hardcoded secrets
cd src/backend
grep -r "AKIA" .  # AWS keys
grep -r "sk-" .   # API keys

# Expected: No matches
```

---

## Performance Verification

### Lambda Metrics to Monitor

```bash
# After deployment, monitor CloudWatch:
# - Invocations
# - Duration (P50, P95, P99)
# - Errors
# - Throttles
# - Memory usage
```

### Performance Targets

| Metric | Target | Production |
|--------|--------|------------|
| Cold start | < 5s | ___ |
| Warm request | < 2s | ___ |
| LLM call | < 30s | ___ |
| Error rate | < 1% | ___ |
| Memory usage | < 400MB | ___ |

---

## Deployment Steps

### Development Environment

```bash
cd infra

# Set environment
export ENVIRONMENT=dev

# Deploy
npx cdk deploy --require-approval never

# Verify deployment
aws lambda get-function --function-name careervp-gap-analysis-dev

# Test endpoint
curl -X POST https://your-api-dev.execute-api.us-east-1.amazonaws.com/dev/api/gap-analysis \
  -H "Authorization: Bearer $DEV_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @test-request.json
```

### Staging Environment

```bash
# Same as dev, with ENVIRONMENT=staging
export ENVIRONMENT=staging
npx cdk deploy --require-approval never
```

### Production Environment

```bash
# IMPORTANT: Get approval before production deploy

export ENVIRONMENT=prod

# Review changes
npx cdk diff

# Deploy with approval
npx cdk deploy

# Smoke test
# Monitor CloudWatch for 15 minutes
```

---

## Post-Deployment Verification

### Smoke Tests

```bash
# 1. Health check (if implemented)
curl https://your-api-prod/health

# 2. Gap analysis endpoint
curl -X POST https://your-api-prod/api/gap-analysis \
  -H "Authorization: Bearer $PROD_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @prod-test-request.json

# 3. Error handling
curl -X POST https://your-api-prod/api/gap-analysis \
  -H "Authorization: Bearer $PROD_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invalid": "request"}'

# Expected: 400 Bad Request
```

### CloudWatch Monitoring

```bash
# Check logs
aws logs tail /aws/lambda/careervp-gap-analysis-prod --follow

# Check metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=careervp-gap-analysis-prod \
  --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## Rollback Plan

### If Issues Detected

```bash
# Option 1: Quick fix and redeploy
git revert HEAD
git push
npx cdk deploy

# Option 2: Rollback to previous version
npx cdk deploy --previous-stack

# Option 3: Disable endpoint
# Update API Gateway to return 503
```

---

## Final Acceptance Criteria

### Before Marking Complete

- [ ] All 70+ tests pass
- [ ] Code coverage ≥90%
- [ ] ruff format passes
- [ ] ruff check passes
- [ ] mypy --strict passes
- [ ] CDK synth succeeds
- [ ] Security checklist complete
- [ ] Documentation complete
- [ ] Deployed to dev successfully
- [ ] Smoke tests pass
- [ ] CloudWatch metrics healthy
- [ ] No errors in logs
- [ ] Architect verification obtained

---

## Success Criteria Summary

### Functional Requirements

✅ POST /api/gap-analysis generates 3-5 targeted questions
✅ Questions scored by impact × probability
✅ Questions sorted by gap_score (descending)
✅ Maximum 5 questions returned
✅ Hebrew language support
✅ LLM timeout handling (600s max)
✅ Error responses follow spec

### Technical Requirements

✅ All tests pass (70+)
✅ Code coverage ≥90%
✅ Type checking passes (mypy --strict)
✅ Linting passes (ruff)
✅ CDK infrastructure valid

### Security Requirements

✅ File size validation (10MB)
✅ JWT authentication
✅ User isolation
✅ Input sanitization

### Performance Requirements

✅ Cold start < 5s
✅ Warm request < 2s
✅ Total latency < 35s

---

## Commit Message

```bash
git add .
git commit -m "feat(gap-analysis): Phase 11 complete and production ready

Summary:
- POST /api/gap-analysis endpoint implemented
- 3-5 targeted questions generated via Claude Haiku
- Gap scoring algorithm (impact × probability)
- Synchronous implementation (no SQS)
- 10MB file size validation
- JWT authentication and user isolation

Tests:
- 70+ tests passing (unit, integration, infrastructure, E2E)
- 92% code coverage
- All security tests pass

Infrastructure:
- Lambda: careervp-gap-analysis-{env} (120s timeout, 512MB)
- API Gateway: POST /api/gap-analysis
- Cognito authorization

Documentation:
- Architecture: GAP_ANALYSIS_DESIGN.md
- Specification: GAP_SPEC.md
- Tasks: 9 task files with implementation guidance

Compliance:
- Rule 1 & 4: Layered Monarchy (Handler → Logic → DAL)
- Rule 2: 10MB file size limit enforced
- Rule 5: Result[T] pattern used throughout
- AWS Powertools observability

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Handoff to Architect

Once all criteria met, request final architect verification:

**Architect Verification Checklist:**
- [ ] Architecture patterns followed
- [ ] Security requirements met
- [ ] Performance acceptable
- [ ] Code quality high
- [ ] Documentation complete
- [ ] Tests comprehensive
- [ ] Production ready

✅ **Phase 11 Complete**
