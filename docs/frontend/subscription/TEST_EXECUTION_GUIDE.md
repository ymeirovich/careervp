# Subscription Service — Test Execution Guide

This guide provides step-by-step instructions for running the subscription service test suite both automatically and manually.

---

## Quick Start

### Setup
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/frontend
npm install
```

### Run All Tests
```bash
npm test
```

**Expected output:**
```
PASS  src/frontend/tests/unit/trial.test.ts
PASS  src/frontend/tests/unit/checkout.test.ts
...
Test Suites: 28 passed, 28 total
Tests:       129 passed, 129 total
Time:        45.2s
```

---

## Automated Test Modes

### 1. Unit Tests Only
```bash
npm run test:unit
```

**What it tests:** Logic validation, mocked APIs, no external dependencies
**Duration:** ~30 seconds
**Test files:**
- `src/frontend/tests/unit/trial.test.ts` (3 tests: F-SUB-001, 002, 003)
- `src/frontend/tests/unit/checkout.test.ts` (5 tests: F-SUB-004, 005, 006)
- `src/frontend/tests/unit/portal.test.ts` (2 tests: F-SUB-007)
- `src/frontend/tests/unit/subscription-status.test.ts` (3 tests: F-SUB-008, 015)
- `src/frontend/tests/unit/webhook-signature.test.ts` (1 test: F-SUB-009)
- `src/frontend/tests/unit/webhook-checkout.test.ts` (2 tests: F-SUB-010, 011)
- `src/frontend/tests/unit/webhook-invoice.test.ts` (2 tests: F-SUB-012, 013)
- `src/frontend/tests/unit/webhook-subscription-updated.test.ts` (2 tests: F-SUB-014)
- `src/frontend/tests/unit/webhook-subscription-deleted.test.ts` (1 test: F-SUB-016)
- `src/frontend/tests/unit/quota-enforcement.test.ts` (1 test: F-SUB-017)
- `src/frontend/tests/unit/cdk-infra.test.ts` (1 test: F-SUB-018 snapshot)
- `src/frontend/tests/unit/ssm-cold-start.test.ts` (1 test: F-SUB-019)
- `src/frontend/tests/unit/cors.test.ts` (1 test: F-SUB-020)

**Total: 26 unit test cases**

---

### 2. Integration Tests
```bash
npm run test:integration
```

**What it tests:** Lambda → DynamoDB, Stripe API calls, raw body passthrough
**Duration:** ~2 minutes (requires AWS credentials + Stripe test keys)
**Prerequisites:**
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=<your_key>
export AWS_SECRET_ACCESS_KEY=<your_secret>
export STRIPE_SECRET_KEY=sk_test_...
```

**Test files:**
- `src/frontend/tests/integration/checkout.integration.test.ts` (F-SUB-004-INT)
- `src/frontend/tests/integration/webhook-rawbody.integration.test.ts` (F-SUB-009-INT)
- `src/frontend/tests/integration/cdk-deploy.integration.test.ts` (F-SUB-018-INT)

**Total: 3 integration test cases**

---

### 3. E2E Tests
```bash
npm run test:e2e
```

**What it tests:** Full signup → checkout → payment → webhook flow
**Duration:** ~3 minutes (requires Stripe CLI + test user)
**Prerequisites:**

1. Install Stripe CLI:
```bash
brew install stripe/stripe-cli/stripe
# or download from https://stripe.com/docs/stripe-cli
```

2. Authenticate with Stripe:
```bash
stripe login
# Follow prompts to authorize
```

3. Set environment variables:
```bash
export STRIPE_WEBHOOK_SECRET=whsec_test_...
export DEV_API_BASE=https://dev-api.careervp.com
export TEST_USER_EMAIL=test-user@careervp.com
```

4. Start Stripe webhook relay in background:
```bash
stripe listen --forward-to https://dev-api.careervp.com/billing/webhook &
# Output: Ready! Your webhook signing secret is: whsec_test_...
# Save the signing secret
```

5. Run E2E tests:
```bash
npm run test:e2e
```

**Test files:**
- `src/frontend/tests/e2e/checkout-to-active.e2e.test.ts` (F-SUB-010-E2E)
- `src/frontend/tests/e2e/invoice-recovery.e2e.test.ts` (F-SUB-012-E2E)
- `src/frontend/tests/e2e/invoice-past-due.e2e.test.ts` (F-SUB-013-E2E)
- `src/frontend/tests/e2e/subscription-cancellation.e2e.test.ts` (F-SUB-016-E2E)
- `src/frontend/tests/e2e/upgrade-flow.e2e.test.ts` (F-SUB-021)

**Total: 5 E2E test cases**

---

### 4. Regression Tests
```bash
npm run test:regression
```

**What it tests:** Boundary conditions, edge cases, prevention of known issues
**Duration:** ~1 minute

**Test files:**
- `src/frontend/tests/regression/trial-expiry-boundary.regression.test.ts` (F-SUB-002-R)
- `src/frontend/tests/regression/trial-exhausted-boundary.regression.test.ts` (F-SUB-003-R)
- `src/frontend/tests/regression/customer-dedup.regression.test.ts` (F-SUB-005-R)
- `src/frontend/tests/regression/subscription-status-shapes.regression.test.ts` (F-SUB-008-R)
- `src/frontend/tests/regression/webhook-idempotency.regression.test.ts` (F-SUB-011-R)
- `src/frontend/tests/regression/cors-no-wildcard.regression.test.ts` (F-SUB-020-R)
- `src/frontend/tests/regression/upgrade-quarterly.regression.test.ts` (F-SUB-021-R)

**Total: 7 regression test cases (26 sub-cases)**

---

### 5. Coverage Report
```bash
npm run test:coverage
```

**Generates:**
- `coverage/lcov-report/index.html` — Interactive HTML coverage report
- `coverage/lcov.info` — Raw coverage data

**Viewing coverage:**
```bash
npm run test:coverage
open coverage/lcov-report/index.html
```

**Expected coverage targets:**
- `subscription_service.py`: >90%
- `stripe_service.py`: >85%
- `webhook_handlers.py`: >85%
- `billing_handler.py`: >80%

---

## Run Specific Test File

```bash
# Single test file
npx jest src/frontend/tests/unit/trial.test.ts

# Pattern matching
npx jest --testPathPattern="webhook"
npx jest --testNamePattern="F-SUB-010"

# Watch mode (re-run on file changes)
npx jest src/frontend/tests/unit/checkout.test.ts --watch
```

---

## Manual Testing

Manual tests are useful for integration with running infrastructure and real Stripe accounts.

### Prerequisites for Manual Testing

1. **AWS Account & CLI Access:**
```bash
aws sts get-caller-identity  # Verify credentials
export AWS_REGION=us-east-1
```

2. **Stripe Test Mode:**
```bash
# Get test mode API keys from Stripe Dashboard
# Dashboard → Developers → API Keys → Restricted Keys
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLISHABLE_KEY=pk_test_...
```

3. **Cognito Test User:**
```bash
aws cognito-idp list-user-pools --max-results 10 --region us-east-1 | jq '.UserPools[] | select(.Name | contains("careervp"))'

# Get user pool ID
USER_POOL_ID=us-east-1_WiHMRqLpe

# Create test user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username test-user@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS \
  --region us-east-1

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username test-user@example.com \
  --password TestPass123! \
  --permanent \
  --region us-east-1
```

---

### Test 1: Manual Trial Creation & Validation

```bash
# 1. Get JWT token for test user
USER_POOL_ID=us-east-1_WiHMRqLpe
CLIENT_ID=$(aws cognito-idp list-user-pool-clients \
  --user-pool-id $USER_POOL_ID \
  --max-results 5 \
  --region us-east-1 | jq -r '.UserPoolClients[0].ClientId')

JWT=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=test-user@example.com,PASSWORD=TestPass123! \
  --region us-east-1 | jq -r '.AuthenticationResult.IdToken')

echo "JWT Token: $JWT"

# 2. Verify User record created in DynamoDB
aws dynamodb get-item \
  --table-name careervp-users-dev \
  --key '{"user_id": {"S": "test-user@example.com"}}' \
  --region us-east-1 | jq '.Item'

# Expected output:
# {
#   "user_id": { "S": "test-user@example.com" },
#   "created_at": { "S": "2026-03-15T10:30:45Z" },
#   "stripe_customer_id": { "NULL": true }
# }

# 3. Verify Usage record initialized with 3 credits
aws dynamodb get-item \
  --table-name careservp-usage-dev \
  --key '{"user_id": {"S": "test-user@example.com"}}' \
  --region us-east-1 | jq '.Item'

# Expected output:
# {
#   "user_id": { "S": "test-user@example.com" },
#   "remaining": { "N": "3" },
#   "created_at": { "S": "2026-03-15T10:30:45Z" }
# }
```

---

### Test 2: Manual Checkout Session Creation

```bash
# Using JWT from Test 1

# 1. Call checkout endpoint
CHECKOUT_RESPONSE=$(curl -s -X POST https://dev-api.careervp.com/billing/checkout \
  -H "Authorization: $JWT" \
  -H "Content-Type: application/json" \
  -H "Origin: https://app.careervp.com" \
  -d '{
    "plan": "monthly",
    "success_url": "https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
    "cancel_url": "https://app.careervp.com/settings/billing"
  }')

echo "Checkout Response: $CHECKOUT_RESPONSE"

# Expected output:
# {
#   "checkout_url": "https://checkout.stripe.com/pay/cs_test_..."
# }

# 2. Extract checkout URL
CHECKOUT_URL=$(echo $CHECKOUT_RESPONSE | jq -r '.checkout_url')
echo "Visit in browser: $CHECKOUT_URL"

# 3. Verify Stripe customer created
CUSTOMER_ID=$(curl -s -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
  https://api.stripe.com/v1/customers \
  | jq -r '.data[] | select(.metadata.user_id == "test-user@example.com") | .id')

echo "Stripe Customer ID: $CUSTOMER_ID"
```

---

### Test 3: Manual Webhook Processing

```bash
# Prerequisites:
# - Stripe CLI installed and authenticated
# - Webhook relay started: stripe listen --forward-to https://dev-api.careervp.com/billing/webhook

# 1. Trigger test webhook event
stripe trigger checkout.session.completed \
  --override subscription='sub_test_manual_001' \
  --override customer='cus_test_manual_001' \
  --override metadata.user_id='test-user@example.com' \
  --override metadata.plan='monthly'

# 2. Check Lambda logs
aws logs tail /aws/lambda/careervp-billing-dev --follow --region us-east-1

# Expected log:
# [INFO] Subscription activated for user test-user@example.com

# 3. Verify subscription created in DynamoDB
aws dynamodb query \
  --table-name careervp-subscriptions-dev \
  --index-name UserSubscriptionIndex \
  --key-condition-expression "user_id = :uid" \
  --expression-attribute-values '{":uid": {"S": "test-user@example.com"}}' \
  --region us-east-1 | jq '.Items'

# Expected output:
# {
#   "subscription_id": { "S": "sub_test_manual_001" },
#   "status": { "S": "active" },
#   "plan": { "S": "monthly" },
#   "remaining": { "N": "9999" }  ← Unlimited access
# }

# 4. Verify usage updated to unlimited (9999)
aws dynamodb get-item \
  --table-name careervp-usage-dev \
  --key '{"user_id": {"S": "test-user@example.com"}}' \
  --region us-east-1 | jq '.Item.remaining'

# Expected: { "N": "9999" }
```

---

### Test 4: Manual Access Control Validation

```bash
# 1. Create expired trial user (simulate 15 days passed)
aws dynamodb put-item \
  --table-name careervp-users-dev \
  --item '{
    "user_id": {"S": "test-expired-trial"},
    "created_at": {"S": "2026-02-28T00:00:00Z"},
    "stripe_customer_id": {"NULL": true}
  }' \
  --region us-east-1

# 2. Create usage record with 1 credit
aws dynamodb put-item \
  --table-name careervp-usage-dev \
  --item '{
    "user_id": {"S": "test-expired-trial"},
    "remaining": {"N": "1"},
    "created_at": {"S": "2026-02-28T00:00:00Z"}
  }' \
  --region us-east-1

# 3. Get JWT for expired trial user
JWT=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=test-expired-trial,PASSWORD=TestPass123! \
  --region us-east-1 | jq -r '.AuthenticationResult.IdToken')

# 4. Try to create job (should be blocked)
curl -s -X POST https://dev-api.careervp.com/jobs \
  -H "Authorization: $JWT" \
  -H "Content-Type: application/json" \
  -d '{"title": "Software Engineer", "company": "Acme Inc"}' \
  | jq '.'

# Expected response: 403 trial_expired
# {
#   "error": "trial_expired",
#   "message": "Your trial has expired"
# }
```

---

### Test 5: Manual CORS Validation

```bash
# 1. Test allowed origin
curl -s -X OPTIONS https://dev-api.careervp.com/billing/checkout \
  -H "Origin: https://app.careervp.com" \
  -H "Access-Control-Request-Method: POST" | grep -i "Access-Control-Allow-Origin"

# Expected:
# Access-Control-Allow-Origin: https://app.careervp.com

# 2. Test disallowed origin
curl -s -X OPTIONS https://dev-api.careervp.com/billing/checkout \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: POST" | grep -i "Access-Control-Allow-Origin"

# Expected: (no header)

# 3. Test webhook (should have no CORS header)
curl -s -X OPTIONS https://dev-api.careervp.com/billing/webhook \
  -H "Origin: https://app.careervp.com" | grep -i "Access-Control-Allow-Origin"

# Expected: (no header)
```

---

## Debugging Test Failures

### Check Test Output Detail
```bash
npm test -- --verbose
```

### Run with Console Output
```bash
npm test -- --forceExit --verbose
```

### Debug Single Test
```bash
node --inspect-brk ./node_modules/.bin/jest --runInBand src/frontend/tests/unit/trial.test.ts
# Opens Chrome DevTools on chrome://inspect
```

### View Jest Coverage Gaps
```bash
npm run test:coverage
cat coverage/lcov-report/index.html  # Open in browser
```

### Check Mock Calls
Add to test:
```typescript
expect(mockDal.get_user).toHaveBeenCalledWith('user-123');
expect(mockDal.get_user).toHaveBeenCalledTimes(1);
console.log(mockDal.get_user.mock.calls);  // Inspect all calls
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Test Subscription Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: 18
      - run: cd src/frontend && npm install
      - run: npm run test:unit
      - run: npm run test:regression
      - run: npm run test:coverage
```

---

## Performance & Optimization

### Test Execution Times (Target)
| Mode | Duration | Notes |
|------|----------|-------|
| Unit | <30s | In-memory, no I/O |
| Integration | <2m | AWS API calls, cached |
| E2E | <3m | Real Stripe, webhook wait |
| Regression | <1m | Parallelized boundary cases |
| **Total** | **<7m** | All tests combined |

### Optimize Slow Tests
```bash
# Find slowest tests
npm test -- --listTests | while read test; do
  echo "Testing: $test"
  time npx jest "$test" --silent
done

# Run tests in parallel
npm test -- --maxWorkers=4
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot find module 'stripe'" | `npm install` in src/frontend |
| "AWS credentials not found" | `aws configure` or set env vars |
| "Stripe webhook not received" | Check `stripe listen` is running; verify webhook secret |
| "DynamoDB table not found" | Deploy CDK stack: `cdk deploy BillingStack --stage dev` |
| "Jest timeout" | Increase timeout: `jest.setTimeout(10000)` in test |
| "Mock not called" | Add `expect(mock).toHaveBeenCalled()` to debug |

---

## Summary

**All tests must pass before deployment:**
```bash
npm test && npm run test:coverage && npm run test:integration && npm run test:e2e
```

**Success criteria:**
- ✅ 129 test cases pass
- ✅ >80% code coverage
- ✅ No console errors
- ✅ All regression tests pass
- ✅ Manual smoke tests pass

---
