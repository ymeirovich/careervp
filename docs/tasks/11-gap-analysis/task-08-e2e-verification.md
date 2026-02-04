# Task 08: End-to-End Verification

## Overview

Verify complete gap analysis flow from API call to result.

**Test files:**
- `tests/gap-analysis/e2e/test_gap_analysis_flow.py` (already created)
- `tests/gap-analysis/infrastructure/test_gap_analysis_stack.py` (already created)

**Dependencies:** All previous tasks (01-07)
**Estimated time:** 2 hours
**Goal:** Verify entire system works end-to-end

---

## E2E Test Scenarios

### Scenario 1: Happy Path

```python
@pytest.mark.e2e
def test_complete_gap_analysis_flow():
    """
    1. POST /api/gap-analysis with valid CV and job posting
    2. Verify 200 OK response
    3. Verify 3-5 questions returned
    4. Verify questions have all required fields
    5. Verify questions sorted by gap_score
    """
```

### Scenario 2: Error Handling

```python
@pytest.mark.e2e
def test_gap_analysis_cv_not_found():
    """
    1. POST with invalid cv_id
    2. Verify 404 Not Found
    3. Verify error message
    """
```

### Scenario 3: Security

```python
@pytest.mark.e2e
def test_user_isolation():
    """
    1. User A submits gap analysis
    2. User B tries to access with different JWT
    3. Verify isolation enforced
    """
```

---

## Infrastructure Tests

### CDK Stack Verification

```bash
cd infra

# Synthesize stack
npx cdk synth

# Run infrastructure tests
cd ..
uv run pytest tests/gap-analysis/infrastructure/ -v

# Expected: All infrastructure assertions pass
```

### Infrastructure Checklist

- [ ] Lambda function exists with correct name
- [ ] Lambda timeout = 120 seconds
- [ ] Lambda memory = 512 MB
- [ ] API Gateway route exists: POST /api/gap-analysis
- [ ] Cognito authorization configured
- [ ] DynamoDB permissions granted
- [ ] Environment variables set

---

## Manual E2E Testing (Optional)

### Using AWS CLI

```bash
# Get JWT token from Cognito
JWT_TOKEN="<your-jwt-token>"

# Call API
curl -X POST https://your-api.execute-api.us-east-1.amazonaws.com/dev/api/gap-analysis \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "cv_id": "cv_789",
    "job_posting": {
      "company_name": "Test Corp",
      "role_title": "Software Engineer",
      "requirements": ["Python", "AWS"],
      "responsibilities": [],
      "nice_to_have": [],
      "language": "en"
    },
    "language": "en"
  }'

# Expected: 200 OK with questions array
```

---

## Performance Verification

### Latency Targets

| Metric | Target | Measured |
|--------|--------|----------|
| Cold start | < 5s | ___ |
| Warm invocation | < 2s | ___ |
| LLM processing | < 30s | ___ |
| Total end-to-end | < 35s | ___ |

### Load Testing (Optional)

```bash
# Install Artillery
npm install -g artillery

# Create load test config
artillery quick --count 10 --num 5 https://your-api/gap-analysis

# Target: 10 users, 5 requests each
# Expected: <5% error rate, <35s P95 latency
```

---

## Verification Commands

```bash
cd src/backend

# Run all E2E tests
uv run pytest tests/gap-analysis/e2e/ -v --tb=short

# Run infrastructure tests
uv run pytest tests/gap-analysis/infrastructure/ -v

# Run full test suite
uv run pytest tests/gap-analysis/ -v

# Check coverage
uv run pytest tests/gap-analysis/ --cov=careervp --cov-report=html

# Open coverage report
open htmlcov/index.html
```

---

## Acceptance Criteria

### Functional
- [ ] E2E happy path test passes
- [ ] Error handling tests pass
- [ ] Security tests pass
- [ ] Infrastructure tests pass
- [ ] Manual testing successful (optional)

### Performance
- [ ] Cold start < 5 seconds
- [ ] Warm invocation < 2 seconds
- [ ] Total latency < 35 seconds
- [ ] No timeout errors

### Quality
- [ ] All 60+ tests pass
- [ ] Code coverage ≥90%
- [ ] No flaky tests
- [ ] No memory leaks
- [ ] CloudWatch logs clean

---

## Troubleshooting

### E2E Tests Failing

**Check:**
1. Environment variables set correctly
2. Mocks configured properly
3. Test fixtures valid
4. DynamoDB local running (if needed)

### Infrastructure Tests Failing

**Check:**
1. CDK synth succeeds
2. Lambda function names match
3. API Gateway routes configured
4. IAM permissions correct

### Performance Issues

**Check:**
1. Lambda memory sufficient (512MB)
2. LLM model (use Haiku, not Opus)
3. DynamoDB indexes optimized
4. Cold start optimizations

---

## Commit Message

```bash
git commit -m "test(gap-analysis): add E2E and infrastructure tests

- Add E2E flow tests (8 tests)
- Add infrastructure CDK tests (10 tests)
- Verify happy path, errors, security
- All E2E tests pass
- All infrastructure tests pass
- Total: 68 tests passing

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
