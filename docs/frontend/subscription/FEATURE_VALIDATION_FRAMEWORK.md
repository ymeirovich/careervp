# Subscription Service — Feature Validation Framework

**Purpose:** Define EXACTLY how to validate that each feature (F-SUB-001 through F-SUB-021) is implemented 100% correctly, not just that tests pass.

---

## Validation Hierarchy

There are 4 levels of validation. Each builds on the previous:

### Level 1: Unit Tests Pass ✓
**What it proves:** Logic is correct in isolation
**What it does NOT prove:** Works with real dependencies, no side effects, integrates properly

### Level 2: Integration Tests Pass ✓
**What it proves:** Works with real DynamoDB, Lambda environment
**What it does NOT prove:** Full end-to-end flow, concurrent operations, webhook ordering

### Level 3: Code Quality Standards ✓
**What it proves:** Implementation follows patterns, maintainable, no breaking changes
**What it does NOT prove:** Handles all edge cases, performs under load

### Level 4: Full System Validation ✓
**What it proves:** Feature works in context of entire system
**What it does NOT prove:** Production readiness (needs additional monitoring setup)

**100% Implementation = ALL FOUR LEVELS PASSING**

---

## Level 1: Unit Test Validation

### For Each Feature (F-SUB-001 through F-SUB-021):

| Feature | Test File | Command | Must Pass |
|---------|-----------|---------|-----------|
| F-SUB-001 | unit/trial.test.ts | `npm test -- trial.test.ts --testNamePattern="F-SUB-001"` | All assertions |
| F-SUB-002 | unit/trial.test.ts | `npm test -- trial.test.ts --testNamePattern="F-SUB-002"` | All assertions |
| F-SUB-003 | unit/trial.test.ts | `npm test -- trial.test.ts --testNamePattern="F-SUB-003"` | All assertions |
| ... | ... | ... | ... |
| F-SUB-021 | e2e/upgrade-flow.e2e.test.ts | `npm test -- upgrade-flow.e2e.test.ts --testNamePattern="F-SUB-021"` | All assertions |

### Validation Checklist for Each Test:

```
Feature: F-SUB-XXX
Test File: [file].test.ts
Status: [ ] FAIL [ ] PASS [ ] SKIP

Preconditions Met:
  [ ] All mock data loaded correctly
  [ ] DynamoDB tables mocked with correct schema
  [ ] Stripe mocked with correct response
  [ ] Cognito JWT extraction working

Assertions Verified:
  [ ] HTTP status code correct
  [ ] Response body matches spec
  [ ] Error codes match spec (if error case)
  [ ] DynamoDB writes/updates occurred (if data mutated)
  [ ] Side effects (emails, webhooks) triggered correctly
  [ ] No unintended side effects

Test Execution:
  [ ] Ran with `npm test -- [file].test.ts`
  [ ] No timeouts or flakes
  [ ] Passed on first run
  [ ] Passed on subsequent runs (idempotency check)

Coverage:
  [ ] Test execution path reaches all branches
  [ ] No skipped assertions (no .only or .skip)
  [ ] All error cases tested (happy path + error paths)
```

### Unit Test Command Summary:
```bash
# Run all unit tests
npm run test:unit

# Run specific feature
npm test -- trial.test.ts --testNamePattern="F-SUB-001"

# Run with coverage
npm run test:coverage

# Expected: 129+ tests passing, >80% coverage
```

---

## Level 2: Integration Test Validation

### For Each Integration Test Group:

| Test ID | Test File | Dependency | Command |
|---------|-----------|-----------|---------|
| F-SUB-004-INT | integration/checkout.integration.test.ts | AWS Credentials, Stripe Secret | `npm run test:integration` |
| F-SUB-009-INT | integration/webhook-rawbody.integration.test.ts | AWS, API Gateway | `npm run test:integration` |
| F-SUB-018-INT | integration/cdk-deploy.integration.test.ts | AWS, CDK CLI | `npm run test:integration` |

### Integration Test Setup:
```bash
# Prerequisites
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=<dev_key>
export AWS_SECRET_ACCESS_KEY=<dev_secret>
export STRIPE_SECRET_KEY=sk_test_...

# Run integration tests
npm run test:integration

# Verify database state
aws dynamodb scan --table-name careervp-users-dev --region us-east-1
aws dynamodb scan --table-name careervp-usage-dev --region us-east-1
aws dynamodb scan --table-name careervp-subscriptions-dev --region us-east-1
```

### Integration Validation Checklist:

```
Test: F-SUB-004-INT (Checkout Integration)

Pre-Test State:
  [ ] AWS credentials valid (aws sts get-caller-identity)
  [ ] DynamoDB tables exist (dev stage)
  [ ] Stripe test mode enabled
  [ ] Lambda environment variables set
  [ ] API Gateway endpoint accessible

During Test:
  [ ] Lambda invoked successfully
  [ ] No timeouts (30s threshold)
  [ ] Stripe API called correctly
  [ ] DynamoDB write successful
  [ ] Response returned within SLA

Post-Test Verification:
  [ ] DynamoDB records created correctly
  [ ] Stripe customer ID stored
  [ ] No residual test data (cleanup)
  [ ] CloudWatch logs show no errors
  [ ] Checkout URL format valid

Regression Check:
  [ ] F-SUB-001, 002, 003 still passing (Group 1)
  [ ] /jobs endpoint still working (existing functionality)
  [ ] No new errors in CloudWatch
```

### Integration Test Command Summary:
```bash
npm run test:integration

# Expected: 3 integration tests passing
# CloudWatch: No error logs
# DynamoDB: Test data cleaned up or clearly marked
```

---

## Level 3: Code Quality & Architecture Validation

### For Each Implementation Group:

**Group 1 (S-001): Trial & Quota**
- **Files to Review:**
  - src/backend/careervp/logic/subscription_service.py
  - src/backend/careervp/models/usage.py
  - src/backend/careervp/models/user.py

- **Code Quality Checklist:**

```
Shared Data Models (User, Usage, Subscription):
  [ ] Dataclass with @dataclass decorator
  [ ] Type hints on all fields
  [ ] Immutable fields (frozen=True where appropriate)
  [ ] String representations (__repr__)
  [ ] Validation methods (e.g., trial_expired property)

Business Logic (subscription_service.py):
  [ ] Pure functions (no side effects except DAL calls)
  [ ] Clear function signatures with type hints
  [ ] Docstrings explaining logic
  [ ] Error handling with ApiError
  [ ] No magic numbers (constants defined)

DAL Layer (subscriptions_dal.py, users_dal.py, usage_dal.py):
  [ ] Consistent interface (CRUD methods)
  [ ] DynamoDB operations wrapped properly
  [ ] Error handling for missing items
  [ ] Index queries use proper GSIs
  [ ] Transaction support where needed

Handler Layer (billing_handler.py):
  [ ] Cognito JWT extraction correct
  [ ] Request validation before business logic
  [ ] try/except with proper error responses
  [ ] Logging for debugging
  [ ] CORS headers applied correctly
```

### Architecture Compliance:

```
Request-Response Pipeline:
  [ ] Cognito → JWT extraction working
  [ ] API Gateway → Raw body passthrough for webhooks
  [ ] Lambda → Correct handler invoked
  [ ] DAL → Correct table/index queried
  [ ] Response → CORS headers + status code correct

Data Model Consistency:
  [ ] User.created_at never updated (immutable)
  [ ] Usage.remaining never goes negative
  [ ] Subscription.subscription_id is primary key (unique)
  [ ] All timestamps ISO 8601 or Unix (never mixed)
  [ ] Enums used for status/plan values

Error Handling:
  [ ] All errors mapped to correct HTTP codes
  [ ] Error messages are helpful to client
  [ ] Errors don't leak internal details
  [ ] Stack traces only in CloudWatch, not responses

No Breaking Changes:
  [ ] /jobs endpoint still works (quota check added)
  [ ] /gap-analyses endpoint still works
  [ ] Response formats unchanged for existing endpoints
  [ ] Database schema backwards compatible
```

### Code Review Checklist:

```
Readability:
  [ ] Variable names are descriptive
  [ ] Functions do one thing (SRP)
  [ ] No deeply nested code (max 3 levels)
  [ ] Comments explain WHY, not WHAT

Performance:
  [ ] N+1 queries avoided (batch operations)
  [ ] DynamoDB indexes used for queries
  [ ] No unnecessary table scans
  [ ] Lambda memory sufficient (512MB+ for Stripe)

Security:
  [ ] No secrets hardcoded (all from SSM/env)
  [ ] CORS whitelist enforced (no *)
  [ ] Webhook signature verified
  [ ] No SQL injection (using DAL, not raw queries)
  [ ] User data validated before use

Testing:
  [ ] Unit tests cover happy + error paths
  [ ] Integration tests verify data persistence
  [ ] E2E tests cover user workflows
  [ ] Regression tests catch boundary cases
```

### Code Quality Command Summary:
```bash
# Run linter
cd src/backend && ruff check careervp --fix

# Run type checker
cd src/backend && mypy careervp --strict

# Run tests with coverage
npm run test:coverage

# Expected: 0 linter errors, 0 type errors, >80% coverage
```

---

## Level 4: Full System Validation

### End-to-End Workflow Validation:

#### E2E Test 1: Signup → Trial Creation → Job Creation
```bash
Test: F-SUB-001-E2E (implied, not explicit)

Steps:
  1. Signup user in Cognito
  2. Call POST /jobs with trial user
  3. Verify job created successfully
  4. Check DynamoDB: User.created_at exists, Usage.remaining = 2
  5. Create 3 jobs total
  6. Attempt 4th job
  7. Verify 403 trial_exhausted

Validation:
  [ ] DynamoDB User record created
  [ ] DynamoDB Usage record created with remaining=3
  [ ] First 3 jobs created successfully
  [ ] 4th job returns 403
  [ ] Usage.remaining decrements correctly (3→0)
```

#### E2E Test 2: Trial Expiry → Access Blocked
```bash
Test: F-SUB-002-E2E (via regression test)

Setup:
  - Create user with created_at = 15 days ago
  - Remaining = 5 (plenty of credits)

Steps:
  1. Call POST /jobs with expired trial user
  2. Verify 403 trial_expired

Validation:
  [ ] Even with credits, access is blocked
  [ ] Correct error code returned
  [ ] No job created
```

#### E2E Test 3: Checkout → Subscription Active → Unlimited Access
```bash
Test: F-SUB-010-E2E (Checkout to Active)

Setup:
  - Trial user (remaining=0, created_at=2 days ago)
  - Cognito JWT valid

Steps:
  1. POST /billing/checkout with plan=monthly
  2. Get checkout_url from response
  3. Simulate Stripe payment (test card 4242...)
  4. Verify webhook received (Stripe CLI)
  5. GET /users/me/subscription → status=active
  6. POST /jobs → succeeds (not blocked)
  7. Check usage.remaining = 9999

Validation:
  [ ] Stripe Customer created (no duplicate)
  [ ] Checkout session created
  [ ] Webhook signature verified
  [ ] Subscription record created (active)
  [ ] Usage set to unlimited (9999)
  [ ] Full access restored
```

#### E2E Test 4: Webhook Idempotency
```bash
Test: F-SUB-011-R (Webhook Idempotency Regression)

Setup:
  - Mock webhook event (checkout.session.completed)
  - Capture webhook signature

Steps:
  1. POST /billing/webhook with event
  2. Verify subscription created (status=active)
  3. POST /billing/webhook with SAME event again
  4. Verify subscription still exists (no duplicate)
  5. Verify status still active (no corruption)

Validation:
  [ ] First webhook processed
  [ ] Second webhook processed (no error)
  [ ] No duplicate subscriptions created
  [ ] Subscription state unchanged
  [ ] Idempotent operation confirmed
```

#### E2E Test 5: Invoice Payment Failed → Past Due State
```bash
Test: F-SUB-013-E2E (Invoice Past Due)

Steps:
  1. Active subscriber with monthly plan
  2. Simulate invoice.payment_failed webhook
  3. Verify subscription status = past_due
  4. Attempt POST /jobs
  5. Verify 403 subscription_inactive

Validation:
  [ ] Subscription status updated to past_due
  [ ] Access blocked despite valid subscription record
  [ ] Correct error code returned
```

### E2E Test Command Summary:
```bash
# Start Stripe CLI webhook relay
stripe listen --forward-to https://dev-api.careervp.com/billing/webhook &

# Run E2E tests
npm run test:e2e

# Expected: 5 E2E tests passing
# CloudWatch: No errors, webhook events logged
# DynamoDB: All state transitions correct
```

### Full System Validation Checklist:

```
All 21 Features Implemented:
  [ ] F-SUB-001 through F-SUB-021 implemented
  [ ] All tests passing (129+)
  [ ] All code reviewed
  [ ] All integration points verified

Data Integrity:
  [ ] No orphaned records in DynamoDB
  [ ] All timestamps ISO 8601 or Unix
  [ ] Status values consistent (enums)
  [ ] User-Subscription relationship maintained
  [ ] User-Usage relationship maintained

Error Handling Complete:
  [ ] All 10 error codes implemented
  [ ] All status codes correct (200, 400, 403, 404, 409, 500)
  [ ] Error messages helpful
  [ ] No stack traces in responses

Security Verified:
  [ ] CORS whitelist (no *)
  [ ] Webhook signature mandatory
  [ ] Secrets from SSM/env (not hardcoded)
  [ ] JWT validation working
  [ ] No data leakage in errors

Performance Acceptable:
  [ ] Lambda warm startup <500ms
  [ ] Cold startup <3s
  [ ] DynamoDB queries <100ms p99
  [ ] No N+1 queries
  [ ] Memory usage <512MB

Observability Ready:
  [ ] CloudWatch Logs for key operations
  [ ] Error logging on failures
  [ ] Metrics for key operations (checkouts, subscriptions)
  [ ] Dashboard created (optional)
  [ ] Alarms configured (optional)
```

---

## Validation Command Sequence

Run this sequence to validate 100% implementation:

```bash
# 1. Unit Tests (30 seconds)
npm run test:unit

# 2. Coverage Report (30 seconds)
npm run test:coverage
# Verify: >80% coverage, all files included

# 3. Integration Tests (2 minutes)
npm run test:integration

# 4. E2E Tests (3 minutes, requires Stripe CLI)
stripe listen --forward-to https://dev-api.careervp.com/billing/webhook &
npm run test:e2e

# 5. Regression Tests (1 minute)
npm run test:regression

# 6. Code Quality
cd src/backend && ruff check careervp
cd src/backend && mypy careervp --strict

# 7. Manual Spot Check (15 minutes)
# Run manual tests from TEST_EXECUTION_GUIDE.md:
# - Manual Trial Creation & Validation
# - Manual Checkout Session Creation
# - Manual Webhook Processing
# - Manual Access Control Validation
# - Manual CORS Validation

# SUCCESS CRITERIA:
# ✅ All automated tests pass (129+)
# ✅ >80% coverage
# ✅ 0 lint errors
# ✅ 0 type errors
# ✅ All manual tests pass
# ✅ DynamoDB state correct
# ✅ CloudWatch shows no errors
# ✅ Webhooks processed correctly
```

---

## Feature Implementation Tracking Table

Use this table to track 100% implementation of all features:

| Feature | Unit | Integration | E2E | Regression | Code Review | Manual Test | Overall |
|---------|------|-------------|-----|-----------|------------|------------|---------|
| F-SUB-001 | ☐ | — | — | — | ☐ | ☐ | ☐ |
| F-SUB-002 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-003 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-004 | ☐ | ☐ | — | — | ☐ | ☐ | ☐ |
| F-SUB-005 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-006 | ☐ | — | — | — | ☐ | ☐ | ☐ |
| F-SUB-007 | ☐ | — | — | — | ☐ | ☐ | ☐ |
| F-SUB-008 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-009 | ☐ | ☐ | — | — | ☐ | ☐ | ☐ |
| F-SUB-010 | ☐ | — | ☐ | — | ☐ | ☐ | ☐ |
| F-SUB-011 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-012 | ☐ | — | ☐ | — | ☐ | ☐ | ☐ |
| F-SUB-013 | ☐ | — | ☐ | — | ☐ | ☐ | ☐ |
| F-SUB-014 | ☐ | — | — | — | ☐ | ☐ | ☐ |
| F-SUB-015 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-016 | ☐ | — | ☐ | — | ☐ | ☐ | ☐ |
| F-SUB-017 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-018 | ☐ | ☐ | — | — | ☐ | ☐ | ☐ |
| F-SUB-019 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-020 | ☐ | — | — | ☐ | ☐ | ☐ | ☐ |
| F-SUB-021 | — | — | ☐ | ☐ | ☐ | ☐ | ☐ |

**Legend:**
- ☐ = Not yet validated
- ☑ = Passed
- — = Not applicable for this feature
- Feature is 100% complete when all applicable ☑ are filled

---

## What "100% Implementation" Actually Means

| Claim | What It Means | How to Verify |
|-------|---------------|---------------|
| "Feature works" | Tests pass | Run test command for that feature |
| "Fully implemented" | Tests + code quality + no regressions | All levels 1-3 passing |
| "Production ready" | Fully implemented + monitored + operational | All levels 1-4 passing |

---

## Failure Modes & Debugging

### If a Unit Test Fails:
1. Check test file for expected input/output
2. Check pseudo-code in SUBSCRIPTION_IMPLEMENTATION_SPECS.md
3. Check mock setup in tests/setup.ts
4. Run test with `--verbose` flag to see assertion details
5. Add console.log to understand state

### If an Integration Test Fails:
1. Verify AWS credentials (aws sts get-caller-identity)
2. Check Lambda CloudWatch logs
3. Check DynamoDB state after test
4. Verify Stripe test credentials
5. Check API Gateway logs for 5xx errors

### If E2E Test Fails:
1. Check Stripe CLI is running and connected
2. Verify webhook signing secret is correct
3. Check Lambda CloudWatch for webhook processing
4. Verify DynamoDB state after webhook
5. Check for timeouts in webhook delivery

---

## Summary: 100% Validation Checklist

```
✅ LEVEL 1: Unit Tests Pass
   └─ Command: npm run test:unit
   └─ Criteria: All 82+ unit test cases pass

✅ LEVEL 2: Integration Tests Pass
   └─ Command: npm run test:integration
   └─ Criteria: AWS/Stripe integrations work

✅ LEVEL 3: Code Quality Standards
   └─ Command: npm run test:coverage + ruff + mypy
   └─ Criteria: >80% coverage, 0 lints, 0 type errors

✅ LEVEL 4: Full System Validation
   └─ Command: npm run test:e2e + manual tests
   └─ Criteria: E2E flows work, manual tests pass

✅ FEATURE TRACKING
   └─ Mark feature complete only when ALL FOUR LEVELS passing
   └─ Use tracking table above

✅ 100% IMPLEMENTATION
   └─ All 21 features at 100%
   └─ All 129 tests passing
   └─ Zero regressions in existing functionality
```

