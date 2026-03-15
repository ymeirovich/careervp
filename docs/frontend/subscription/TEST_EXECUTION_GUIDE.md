# Subscription Service — Test Execution Guide

Step-by-step instructions for running every tier of the subscription service test suite.

---

## Setup

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/frontend
npm install
```

> **Common mistake:** If you see `npm error Missing script`, verify you are inside
> `src/frontend/`, not the project root or `docs/frontend/`.

---

## Test Suite Overview

Two independent test suites exist:

| Suite | Command | Tests | Purpose |
|-------|---------|-------|---------|
| **Happy-path** | `npm run test:unit` etc. | 129 | Spec compliance (F-SUB-001–021) |
| **Critical hardening** | `npm run test:critical` | ~120 | Edge cases, resilience, security |

Happy-path tests should **always pass**. Critical tests will **fail** until the backend implements the corresponding hardening described in `CRITICAL_CONSIDERATIONS.md`.

---

## All Available Commands

```bash
# ── Happy-path (spec compliance) ─────────────────────────
npm run test:unit          # 13 unit test files  (~30s)
npm run test:integration   # 3 integration files (~2m, needs AWS + Stripe)
npm run test:e2e           # 5 E2E files         (~3m, needs Stripe CLI)
npm run test:regression    # 7 regression files  (~1m)
npm run test:coverage      # All above + HTML coverage report

# ── Critical hardening (edge cases) ──────────────────────
npm run test:critical      # 22 automatable critical tests (~2m)
npm run test:security      # 2 security tests (~30s)

# ── Requires env flags ────────────────────────────────────
PERF_TEST=true npm run test:perf       # Load tests (100 concurrent)
OPS_TEST=true  npm run test:ops        # Deployment/ops validation

# ── Utilities ─────────────────────────────────────────────
npm test                   # All happy-path tests (unit+int+e2e+regression)
npm run test:all           # Every test including critical/perf/ops/security
npm run test:watch         # Watch mode for development
```

---

## Happy-Path Tests (F-SUB-001 → F-SUB-021)

### 1. Unit Tests
```bash
npm run test:unit
```
**Duration:** ~30s | **Deps:** None (all mocked)

| File | Features | ~Cases |
|------|----------|--------|
| `unit/trial.test.ts` | F-SUB-001, 002, 003 | 8 |
| `unit/checkout.test.ts` | F-SUB-004, 005, 006 | 10 |
| `unit/portal.test.ts` | F-SUB-007 | 4 |
| `unit/subscription-status.test.ts` | F-SUB-008, 015 | 6 |
| `unit/webhook-signature.test.ts` | F-SUB-009 | 4 |
| `unit/webhook-checkout.test.ts` | F-SUB-010, 011 | 6 |
| `unit/webhook-invoice.test.ts` | F-SUB-012, 013 | 6 |
| `unit/webhook-subscription-updated.test.ts` | F-SUB-014 | 4 |
| `unit/webhook-subscription-deleted.test.ts` | F-SUB-016 | 3 |
| `unit/quota-enforcement.test.ts` | F-SUB-017 | 4 |
| `unit/cdk-infra.test.ts` | F-SUB-018 | 3 |
| `unit/ssm-cold-start.test.ts` | F-SUB-019 | 4 |
| `unit/cors.test.ts` | F-SUB-020 | 4 |

### 2. Integration Tests
```bash
npm run test:integration
```
**Duration:** ~2m | **Deps:** AWS credentials, Stripe test key

```bash
export AWS_REGION=us-east-1
export STRIPE_SECRET_KEY=sk_test_...
```

| File | Feature | What it hits |
|------|---------|-------------|
| `integration/checkout.integration.test.ts` | F-SUB-004-INT | Stripe API, DynamoDB |
| `integration/webhook-rawbody.integration.test.ts` | F-SUB-009-INT | API Gateway raw body |
| `integration/cdk-deploy.integration.test.ts` | F-SUB-018-INT | CDK stack |

### 3. E2E Tests
```bash
# Terminal 1 — start webhook relay first
stripe listen --forward-to https://dev-api.careervp.com/billing/webhook

# Terminal 2
npm run test:e2e
```
**Duration:** ~3m | **Deps:** Stripe CLI, dev API, Cognito test user

| File | Feature | Flow |
|------|---------|------|
| `e2e/checkout-to-active.e2e.test.ts` | F-SUB-010-E2E | Checkout → webhook → active |
| `e2e/invoice-recovery.e2e.test.ts` | F-SUB-012-E2E | Failed → recovered invoice |
| `e2e/invoice-past-due.e2e.test.ts` | F-SUB-013-E2E | Invoice failure → past_due |
| `e2e/subscription-cancellation.e2e.test.ts` | F-SUB-016-E2E | Cancel → blocked |
| `e2e/upgrade-flow.e2e.test.ts` | F-SUB-021 | Full signup → upgrade flow |

### 4. Regression Tests
```bash
npm run test:regression
```
**Duration:** ~1m | **Deps:** None

| File | Feature | Boundary tested |
|------|---------|----------------|
| `regression/trial-expiry-boundary.regression.test.ts` | F-SUB-002-R | Exactly 14 days |
| `regression/trial-exhausted-boundary.regression.test.ts` | F-SUB-003-R | 1 vs 0 credits |
| `regression/customer-dedup.regression.test.ts` | F-SUB-005-R | No duplicate customers |
| `regression/subscription-status-shapes.regression.test.ts` | F-SUB-008-R | All 5 status values |
| `regression/webhook-idempotency.regression.test.ts` | F-SUB-011-R | Duplicate events |
| `regression/cors-no-wildcard.regression.test.ts` | F-SUB-020-R | No `*` origin |
| `regression/upgrade-quarterly.regression.test.ts` | F-SUB-021-R | Quarterly plan path |

### 5. Coverage Report
```bash
npm run test:coverage
open coverage/lcov-report/index.html
```
**Target:** >80% coverage for billing module

---

## Critical Hardening Tests (CC-001 → SEC-003)

These tests document **expected hardened behavior** and will **fail until the backend implements the corresponding hardening**. See `CRITICAL_CONSIDERATIONS.md` for what each needs.

### Critical Tests (Automatable)
```bash
npm run test:critical
```
**Duration:** ~2m | **Deps:** None (all mocked)

#### Transaction Safety & Idempotency

| File | ID | Passes when... |
|------|----|---------------|
| `integration/concurrent-checkout.integration.test.ts` | CC-001 | DynamoDB conditional expressions prevent duplicate customers |
| `integration/race-condition-check-create.integration.test.ts` | CC-002 | Check-then-act uses atomic conditional write |
| `integration/stripe-idempotency.integration.test.ts` | CC-003 | All Stripe calls include `idempotency_key` |

#### Backward Compatibility

| File | ID | Passes when... |
|------|----|---------------|
| `unit/backward-compat-missing-subscription.test.ts` | CC-004 | `check_trial_and_quota()` handles `null` subscription gracefully |
| `unit/backward-compat-missing-usage.test.ts` | CC-005 | Missing Usage record returns `500 usage_not_found`, not crash |
| `unit/backward-compat-partial-data.test.ts` | CC-006 | Missing User record returns `500 user_not_found` |

#### Stripe Error Handling

| File | ID | Passes when... |
|------|----|---------------|
| `integration/stripe-error-503-session.integration.test.ts` | CC-007 | Stripe 503 mapped to `503 payment_provider_unavailable` |
| `integration/stripe-error-503-customer.integration.test.ts` | CC-008 | Stripe 503 on customer create → 503, no partial user update |
| `integration/stripe-timeout.integration.test.ts` | CC-009 | Stripe timeout at 10s → `503 payment_provider_timeout` |
| `integration/stripe-rate-limit-429.integration.test.ts` | CC-010 | Stripe 429 → `503 please_retry_later` + `Retry-After` header |

#### Webhook Delivery Order

| File | ID | Passes when... |
|------|----|---------------|
| `unit/webhook-out-of-order.test.ts` | CC-011 | Events processed in any order converge to correct state |
| `unit/webhook-stale-data-out-of-order.test.ts` | CC-012 | Timestamps gate updates; stale events cannot overwrite newer data |

#### Data Consistency

| File | ID | Passes when... |
|------|----|---------------|
| `integration/partial-failure-customer-created.integration.test.ts` | CC-013 | DynamoDB failure after Stripe success is logged + recoverable |
| `integration/partial-failure-usage-fails.integration.test.ts` | CC-014 | Usage write failure is logged + flagged for manual fix |
| `integration/partial-failure-rollback.integration.test.ts` | CC-015 | Retry reuses existing customer, creates no duplicate |

#### Stripe State vs App State

| File | ID | Passes when... |
|------|----|---------------|
| `integration/subscription-cache-stale.integration.test.ts` | CC-016 | Cache older than 30 min triggers fresh query |
| `integration/state-divergence-detection.integration.test.ts` | CC-017 | DynamoDB/Stripe mismatch emits `subscription_state_divergence` metric |
| `integration/state-reconciliation.integration.test.ts` | CC-018 | Reconciliation updates DynamoDB to match Stripe (Stripe wins) |

#### Lifecycle Edge Cases

| File | ID | Passes when... |
|------|----|---------------|
| `integration/lifecycle-resubscribe-after-cancel.integration.test.ts` | CC-019 | Canceled user can re-subscribe; new `subscription_id` created |
| `unit/lifecycle-trial-no-restart.test.ts` | CC-020 | Trial window is lifetime per-user; does not restart after cancel |

#### Observability

| File | ID | Passes when... |
|------|----|---------------|
| `unit/observability-correlation-id.test.ts` | OBS-001 | Every log line contains `request_id`, `user_id`, `event`, `timestamp` |
| `unit/observability-metrics.test.ts` | OBS-002 | All 6 business metrics (`checkout_attempt`, `checkout_success`, etc.) emitted |

### Security Tests
```bash
npm run test:security
```
**Duration:** ~30s | **Deps:** None

| File | ID | Passes when... |
|------|----|---------------|
| `security/security-rate-limit-webhook.test.ts` | SEC-002 | Webhook returns 429 beyond rate limit threshold |
| `security/security-no-secrets-in-logs.test.ts` | SEC-003 | No `sk_`, `whsec_` or credentials appear in log output |

### Performance Tests
```bash
PERF_TEST=true npm run test:perf
```
**Duration:** ~5m | **Skip condition:** Skipped unless `PERF_TEST=true` | **Deps:** Running API endpoint

| File | ID | Passes when... |
|------|----|---------------|
| `perf/load-test-concurrent-checkouts.perf.test.ts` | PERF-001 | 100 concurrent checkouts: P99 <2s, zero errors, 1 Stripe customer |
| `perf/subscription-query-perf.perf.test.ts` | PERF-002 | Subscription query uses GSI; no full table scan |

### Ops / Deployment Tests
```bash
OPS_TEST=true npm run test:ops
```
**Duration:** ~2m | **Skip condition:** AWS calls skipped unless `OPS_TEST=true` | **Deps:** AWS credentials, deployed stack

| File | ID | What it verifies |
|------|----|-----------------|
| `ops/alarm-configuration.ops.test.ts` | OBS-003 | CloudWatch alarms exist for error rate, latency, divergence |
| `ops/security-webhook-secret-rotation.ops.test.ts` | SEC-001 | Webhook secret in Secrets Manager; rotation documented |
| `ops/staging-validation-different-secrets.ops.test.ts` | STAGE-001 | Staging uses `sk_test_` key, not live key |
| `ops/staging-smoke-test.ops.test.ts` | STAGE-002 | Full E2E smoke test against staging URL |
| `ops/canary-deployment.ops.test.ts` | STAGE-003 | Lambda alias configured for weighted canary routing |
| `ops/rollback-procedure.ops.test.ts` | STAGE-004 | Previous Lambda version exists; rollback documented |

---

## Payload Files Reference

34 JSON fixtures in `tests/payloads/`:

### Happy-Path Payloads (22)
`trial-active`, `trial-expired`, `trial-exhausted`, `checkout-monthly-request`, `checkout-quarterly-request`, `checkout-invalid-plan`, `checkout-existing-customer`, `checkout-already-active`, `portal-request`, `portal-no-customer`, `subscription-active`, `subscription-canceling`, `subscription-past-due`, `subscription-canceled`, `subscription-expired`, `webhook-invalid-signature`, `webhook-checkout-completed`, `webhook-invoice-succeeded`, `webhook-invoice-failed`, `webhook-subscription-updated-plan-change`, `webhook-subscription-cancel-scheduled`, `webhook-subscription-deleted`

### Critical Hardening Payloads (12)
`concurrent-checkout-race`, `race-window`, `idempotency-retry`, `backward-compat-old-trial`, `backward-compat-missing-usage`, `backward-compat-partial-data`, `stripe-503-error`, `partial-failure-customer`, `subscription-cache-stale`, `webhook-out-of-order-events`, `lifecycle-resubscribe`, `observability-correlation`

---

## Manual Testing

### Prerequisites
```bash
export AWS_REGION=us-east-1
aws sts get-caller-identity  # verify credentials

export STRIPE_SECRET_KEY=sk_test_...

USER_POOL_ID=us-east-1_WiHMRqLpe
CLIENT_ID=$(aws cognito-idp list-user-pool-clients \
  --user-pool-id $USER_POOL_ID --max-results 1 \
  | jq -r '.UserPoolClients[0].ClientId')

JWT=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=test@example.com,PASSWORD=TestPass123! \
  | jq -r '.AuthenticationResult.IdToken')
```

### Manual: Trial Activation
```bash
aws dynamodb get-item --table-name careervp-users-dev \
  --key '{"user_id":{"S":"test@example.com"}}' | jq '.Item.remaining'
# Expected: {"N":"3"}
```

### Manual: Checkout Session
```bash
curl -s -X POST https://dev-api.careervp.com/billing/checkout \
  -H "Authorization: $JWT" -H "Content-Type: application/json" \
  -H "Origin: https://app.careervp.com" \
  -d '{"plan":"monthly","success_url":"https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}","cancel_url":"https://app.careervp.com/settings/billing"}'
# Expected: {"checkout_url":"https://checkout.stripe.com/..."}
```

### Manual: Webhook Processing
```bash
# Terminal 1
stripe listen --forward-to https://dev-api.careervp.com/billing/webhook

# Terminal 2
stripe trigger checkout.session.completed \
  --override metadata.user_id=test@example.com \
  --override metadata.plan=monthly

# Verify subscription created
aws dynamodb query --table-name careervp-subscriptions-dev \
  --index-name UserSubscriptionIndex \
  --key-condition-expression "user_id = :uid" \
  --expression-attribute-values '{":uid":{"S":"test@example.com"}}' \
  | jq '.Items[0] | {status, plan}'
# Expected: {"status":{"S":"active"},"plan":{"S":"monthly"}}

# Verify unlimited access
aws dynamodb get-item --table-name careervp-usage-dev \
  --key '{"user_id":{"S":"test@example.com"}}' | jq '.Item.remaining'
# Expected: {"N":"9999"}
```

### Manual: Access Control (Expired Trial)
```bash
aws dynamodb put-item --table-name careervp-users-dev \
  --item '{"user_id":{"S":"expired-test"},"created_at":{"S":"2026-02-01T00:00:00Z"}}'
aws dynamodb put-item --table-name careervp-usage-dev \
  --item '{"user_id":{"S":"expired-test"},"remaining":{"N":"2"},"created_at":{"S":"2026-02-01T00:00:00Z"}}'

curl -s -X POST https://dev-api.careervp.com/jobs \
  -H "Authorization: $JWT" -H "Content-Type: application/json" \
  -d '{"title":"Test"}' | jq '.error'
# Expected: "trial_expired"
```

### Manual: CORS Validation
```bash
# Allowed origin
curl -sI -X OPTIONS https://dev-api.careervp.com/billing/checkout \
  -H "Origin: https://app.careervp.com" | grep -i access-control
# Expected: Access-Control-Allow-Origin: https://app.careervp.com

# Blocked origin
curl -sI -X OPTIONS https://dev-api.careervp.com/billing/checkout \
  -H "Origin: https://evil.example.com" | grep -i access-control
# Expected: (no header)

# Webhook (no CORS ever)
curl -sI -X OPTIONS https://dev-api.careervp.com/billing/webhook \
  -H "Origin: https://app.careervp.com" | grep -i access-control
# Expected: (no header)
```

### CloudWatch Logs
```bash
aws logs tail /aws/lambda/careervp-billing-dev --follow --region us-east-1

# Filter by user
aws logs filter-log-events \
  --log-group-name /aws/lambda/careervp-billing-dev \
  --filter-pattern "test@example.com" | jq '.events[].message'
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `npm error Missing script: "test:critical"` | Wrong directory | `cd src/frontend` |
| `Cannot find module 'stripe'` | Deps not installed | `npm install` |
| `No tests found` | Jest config missing directory | Verify `jest.config.ts` includes project for that dir |
| Jest timeout | Stripe mock not resolving | Check mock resolves or rejects |
| `AWS credentials not found` | Env not set | `aws configure` or export vars |
| Stripe webhook not received | CLI not running | Start `stripe listen` in separate terminal |

### Debug a Single Test
```bash
# Verbose
npx jest tests/unit/trial.test.ts --verbose

# By test name
npx jest --testNamePattern="CC-004"

# With Node debugger
node --inspect-brk ./node_modules/.bin/jest --runInBand \
  tests/integration/concurrent-checkout.integration.test.ts
```

---

## Full Deployment Validation Sequence

Run this end-to-end before any production deployment:

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/frontend

# Stage 1: Happy-path (must all pass)
npm run test:unit
npm run test:integration
npm run test:regression
npm run test:coverage          # verify >80%

# Stage 2: Critical hardening (must all pass)
npm run test:critical
npm run test:security

# Stage 3: E2E (requires Stripe CLI)
stripe listen --forward-to https://dev-api.careervp.com/billing/webhook &
npm run test:e2e

# Stage 4: Optional (manual triggers)
PERF_TEST=true npm run test:perf
OPS_TEST=true  npm run test:ops
```

### Success Criteria

| Check | Target |
|-------|--------|
| Happy-path tests | 129/129 pass |
| Critical tests | ~120/120 pass (after hardening) |
| Security tests | 2/2 pass |
| Code coverage | >80% billing module |
| Lint | 0 errors (`ruff check careervp`) |
| Type check | 0 errors (`mypy careervp --strict`) |
| CloudWatch post-deploy | Zero new errors for 30 min |

---

## Test Count Summary

| Suite | Files | ~Cases | Command |
|-------|-------|--------|---------|
| Unit (happy-path) | 13 | 82 | `test:unit` |
| Integration (happy-path) | 3 | 11 | `test:integration` |
| E2E | 5 | 10 | `test:e2e` |
| Regression | 7 | 26 | `test:regression` |
| Unit (critical) | 8 | ~40 | `test:critical` |
| Integration (critical) | 14 | ~56 | `test:critical` |
| Performance | 2 | ~8 | `PERF_TEST=true test:perf` |
| Ops | 6 | ~18 | `OPS_TEST=true test:ops` |
| Security | 2 | ~8 | `test:security` |
| **TOTAL** | **60** | **~259** | |
