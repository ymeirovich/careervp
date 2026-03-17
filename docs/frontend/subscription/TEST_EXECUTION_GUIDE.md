# Subscription Service — Test Execution Guide

Step-by-step instructions for running every tier of the subscription service test suite.

---

## Setup

### TypeScript (Frontend Tests)

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/frontend
npm install
```

> **Common mistake:** If you see `npm error Missing script`, verify you are inside
> `src/frontend/`, not the project root or `docs/frontend/`.

### Python (Backend Tests)

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv sync
```

> **Requires:** `uv` package manager. Install via `curl -LsSf https://astral.sh/uv/install.sh | sh`.

---

## Test Suite Overview

Three independent test suites exist:

| Suite | Language | Command | Tests | Purpose |
|-------|----------|---------|-------|---------|
| **Python backend unit** | Python | `uv run pytest tests/unit/test_subscription_*.py ...` | ~120 | DAL, service, webhook, quota logic |
| **TS happy-path** | TypeScript | `npm run test:unit` etc. | 129 | Spec compliance (F-SUB-001–021) |
| **TS critical hardening** | TypeScript | `npm run test:critical` | ~120 | Edge cases, resilience, security |

Happy-path and Python tests should **always pass**. Critical hardening tests will **fail** until the backend implements the corresponding hardening described in `CRITICAL_CONSIDERATIONS.md`.

---

## Python Backend Tests

All Python tests live in `src/backend/tests/unit/` and follow the `test_trial_enforcement.py` pattern.

### Subscription-Service Test Files

| File | Coverage | ~Cases |
|------|----------|--------|
| `test_subscription_repository.py` | DAL: get, upsert, update, customer_id, payment events | ~40 |
| `test_billing_service.py` | Checkout, portal, customer reuse, duplicate block | ~30 |
| `test_webhook_service.py` | Signature verify, checkout completed, subscription events | ~35 |
| `test_quota_service.py` | Blocked states, trial enforcement, backward compat | ~15 |

### Running Python Tests

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# All subscription service tests (recommended)
uv run pytest tests/unit/test_subscription_repository.py \
              tests/unit/test_billing_service.py \
              tests/unit/test_webhook_service.py \
              tests/unit/test_quota_service.py \
              -v --tb=short

# Individual test file
uv run pytest tests/unit/test_billing_service.py -v

# Filter by feature ID
uv run pytest tests/unit/ -k "F_SUB_005" -v

# Run with markers
uv run pytest tests/unit/ -m unit -v

# With coverage
uv run pytest tests/unit/test_subscription_repository.py \
              tests/unit/test_billing_service.py \
              tests/unit/test_webhook_service.py \
              tests/unit/test_quota_service.py \
              --cov=careervp --cov-report=html
```

### Running All Existing Backend Unit Tests (Including Subscription)

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/unit/ -v --tb=short
```

---

## Running Python + TypeScript Tests in Parallel

Open two terminals. Both sets of tests are independent and can run simultaneously.

**Terminal 1 — Python backend:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/unit/test_subscription_repository.py \
              tests/unit/test_billing_service.py \
              tests/unit/test_webhook_service.py \
              tests/unit/test_quota_service.py \
              -v --tb=short
```

**Terminal 2 — TypeScript frontend:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/frontend
npm run test:unit
```

---

## TypeScript Happy-Path Tests (F-SUB-001 → F-SUB-021)

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
**Duration:** ~2m | **Deps:** AWS credentials, payment provider test config

```bash
export AWS_REGION=us-east-1
export PAYMENT_PROVIDER=placeholder      # or real provider in test env
export PAYMENT_PROVIDER_PLACEHOLDER=true
```

| File | Feature | What it hits |
|------|---------|-------------|
| `integration/checkout.integration.test.ts` | F-SUB-004-INT | Payment provider API, DynamoDB |
| `integration/webhook-rawbody.integration.test.ts` | F-SUB-009-INT | API Gateway raw body |
| `integration/cdk-deploy.integration.test.ts` | F-SUB-018-INT | CDK stack |

### 3. E2E Tests
```bash
# Terminal 1 — start webhook relay first (provider-specific)
# Example with Stripe CLI:
# stripe listen --forward-to https://dev-api.careervp.com/billing/webhook

# Terminal 2
npm run test:e2e
```
**Duration:** ~3m | **Deps:** Payment provider CLI/relay, dev API, Cognito test user

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

## TypeScript Critical Hardening Tests (CC-001 → SEC-003)

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
| `integration/stripe-idempotency.integration.test.ts` | CC-003 | All payment provider calls include `idempotency_key` |

#### Backward Compatibility

| File | ID | Passes when... |
|------|----|---------------|
| `unit/backward-compat-missing-subscription.test.ts` | CC-004 | `check_trial_and_quota()` handles `null` subscription gracefully |
| `unit/backward-compat-missing-usage.test.ts` | CC-005 | Missing Usage record returns `500 usage_not_found`, not crash |
| `unit/backward-compat-partial-data.test.ts` | CC-006 | Missing User record returns `500 user_not_found` |

#### Payment Provider Error Handling

| File | ID | Passes when... |
|------|----|---------------|
| `integration/stripe-error-503-session.integration.test.ts` | CC-007 | Provider 503 mapped to `503 payment_provider_unavailable` |
| `integration/stripe-error-503-customer.integration.test.ts` | CC-008 | Provider 503 on customer create → 503, no partial user update |
| `integration/stripe-timeout.integration.test.ts` | CC-009 | Provider timeout at 10s → `503 payment_provider_timeout` |
| `integration/stripe-rate-limit-429.integration.test.ts` | CC-010 | Provider 429 → `503 please_retry_later` + `Retry-After` header |

#### Webhook Delivery Order

| File | ID | Passes when... |
|------|----|---------------|
| `unit/webhook-out-of-order.test.ts` | CC-011 | Events processed in any order converge to correct state |
| `unit/webhook-stale-data-out-of-order.test.ts` | CC-012 | Timestamps gate updates; stale events cannot overwrite newer data |

#### Data Consistency

| File | ID | Passes when... |
|------|----|---------------|
| `integration/partial-failure-customer-created.integration.test.ts` | CC-013 | DynamoDB failure after provider success is logged + recoverable |
| `integration/partial-failure-usage-fails.integration.test.ts` | CC-014 | Usage write failure is logged + flagged for manual fix |
| `integration/partial-failure-rollback.integration.test.ts` | CC-015 | Retry reuses existing customer, creates no duplicate |

#### Provider State vs App State

| File | ID | Passes when... |
|------|----|---------------|
| `integration/subscription-cache-stale.integration.test.ts` | CC-016 | Cache older than 30 min triggers fresh query |
| `integration/state-divergence-detection.integration.test.ts` | CC-017 | DynamoDB/provider mismatch emits `subscription_state_divergence` metric |
| `integration/state-reconciliation.integration.test.ts` | CC-018 | Reconciliation updates DynamoDB to match provider (provider wins) |

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
| `perf/load-test-concurrent-checkouts.perf.test.ts` | PERF-001 | 100 concurrent checkouts: P99 <2s, zero errors, 1 provider customer |
| `perf/subscription-query-perf.perf.test.ts` | PERF-002 | Subscription query uses single-table sk; no full table scan |

### Ops / Deployment Tests
```bash
OPS_TEST=true npm run test:ops
```
**Duration:** ~2m | **Skip condition:** AWS calls skipped unless `OPS_TEST=true` | **Deps:** AWS credentials, deployed stack

| File | ID | What it verifies |
|------|----|-----------------|
| `ops/alarm-configuration.ops.test.ts` | OBS-003 | CloudWatch alarms exist for error rate, latency, divergence |
| `ops/security-webhook-secret-rotation.ops.test.ts` | SEC-001 | Webhook secret in Secrets Manager; rotation documented |
| `ops/staging-validation-different-secrets.ops.test.ts` | STAGE-001 | Staging uses test credentials, not live credentials |
| `ops/staging-smoke-test.ops.test.ts` | STAGE-002 | Full E2E smoke test against staging URL |
| `ops/canary-deployment.ops.test.ts` | STAGE-003 | Lambda alias configured for weighted canary routing |
| `ops/rollback-procedure.ops.test.ts` | STAGE-004 | Previous Lambda version exists; rollback documented |

---

## Payload Files Reference

34 JSON fixtures in `tests/payloads/`:

### Happy-Path Payloads (22)
`trial-active`, `trial-expired`, `trial-exhausted`, `checkout-monthly-request`, `checkout-quarterly-request`, `checkout-invalid-plan`, `checkout-existing-customer`, `checkout-already-active`, `portal-request`, `portal-no-customer`, `subscription-active`, `subscription-canceling`, `subscription-past-due`, `subscription-canceled`, `subscription-expired`, `webhook-invalid-signature`, `webhook-checkout-completed`, `webhook-invoice-succeeded`, `webhook-invoice-failed`, `webhook-subscription-updated-plan-change`, `webhook-subscription-cancel-scheduled`, `webhook-subscription-deleted`

### Critical Hardening Payloads (12)
`concurrent-checkout-race`, `race-window`, `idempotency-retry`, `backward-compat-old-trial`, `backward-compat-missing-usage`, `backward-compat-partial-data`, `provider-503-error`, `partial-failure-customer`, `subscription-cache-stale`, `webhook-out-of-order-events`, `lifecycle-resubscribe`, `observability-correlation`

---

## Manual Testing

### Prerequisites
```bash
export AWS_REGION=us-east-1
aws sts get-caller-identity  # verify credentials

# Set payment provider config (placeholder for dev/test)
export PAYMENT_PROVIDER=placeholder
export PAYMENT_PROVIDER_PLACEHOLDER=true

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

Trials are stored in the users table at `sk=TRIAL`.

```bash
aws dynamodb get-item \
  --table-name careervp-users-dev \
  --key '{"pk":{"S":"USER#test@example.com"},"sk":{"S":"TRIAL"}}' \
  | jq '.Item.remaining'
# Expected: {"N":"3"}
```

### Manual: Checkout Session
```bash
curl -s -X POST https://dev-api.careervp.com/billing/checkout \
  -H "Authorization: $JWT" -H "Content-Type: application/json" \
  -H "Origin: https://app.careervp.com" \
  -d '{"plan":"monthly","success_url":"https://app.careervp.com/billing/success","cancel_url":"https://app.careervp.com/settings/billing"}'
# Expected: {"checkout_url":"https://..."}
```

### Manual: Webhook Processing

Subscription data is stored in the single users table at `sk=SUBSCRIPTION#CURRENT`.
Usage is stored at `sk=USAGE`. `customer_id` is stored on `sk=PROFILE`.

```bash
# Trigger a checkout.session.completed webhook (provider CLI varies)
# Example for development with a real provider's CLI:
# stripe trigger checkout.session.completed \
#   --override metadata.user_id=test@example.com \
#   --override metadata.plan=monthly

# Verify subscription created (single-table: sk=SUBSCRIPTION#CURRENT)
aws dynamodb get-item \
  --table-name careervp-users-dev \
  --key '{"pk":{"S":"USER#test@example.com"},"sk":{"S":"SUBSCRIPTION#CURRENT"}}' \
  | jq '.Item | {status: .status.S, plan: .plan.S}'
# Expected: {"status":"active","plan":"monthly"}

# Verify unlimited access (single-table: sk=USAGE)
aws dynamodb get-item \
  --table-name careervp-users-dev \
  --key '{"pk":{"S":"USER#test@example.com"},"sk":{"S":"USAGE"}}' \
  | jq '.Item.remaining'
# Expected: {"N":"9999"}

# Verify customer_id stored on PROFILE row
aws dynamodb get-item \
  --table-name careervp-users-dev \
  --key '{"pk":{"S":"USER#test@example.com"},"sk":{"S":"PROFILE"}}' \
  | jq '.Item.customer_id'
# Expected: {"S":"cus_..."}
```

### Manual: Access Control (Expired Trial)
```bash
# Create an expired trial user (single-table: put PROFILE + TRIAL rows)
aws dynamodb put-item \
  --table-name careervp-users-dev \
  --item '{
    "pk":{"S":"USER#expired-test"},
    "sk":{"S":"PROFILE"},
    "created_at":{"S":"2026-02-01T00:00:00Z"}
  }'

aws dynamodb put-item \
  --table-name careervp-users-dev \
  --item '{
    "pk":{"S":"USER#expired-test"},
    "sk":{"S":"USAGE"},
    "remaining":{"N":"2"},
    "created_at":{"S":"2026-02-01T00:00:00Z"}
  }'

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
| `ModuleNotFoundError: careervp` | Wrong Python dir | `cd src/backend` |
| `No tests found` | Jest config missing directory | Verify `jest.config.ts` includes project for that dir |
| Jest timeout | Payment provider mock not resolving | Check mock resolves or rejects |
| `AWS credentials not found` | Env not set | `aws configure` or export vars |
| `uv: command not found` | uv not installed | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### Debug a Single Test

**TypeScript:**
```bash
# Verbose
npx jest tests/unit/trial.test.ts --verbose

# By test name
npx jest --testNamePattern="CC-004"

# With Node debugger
node --inspect-brk ./node_modules/.bin/jest --runInBand \
  tests/integration/concurrent-checkout.integration.test.ts
```

**Python:**
```bash
# Single test file verbose
uv run pytest tests/unit/test_billing_service.py -v

# Single test by name
uv run pytest tests/unit/test_billing_service.py -k "test_checkout_monthly" -v

# Show captured stdout
uv run pytest tests/unit/test_billing_service.py -v -s

# Stop after first failure
uv run pytest tests/unit/ -x --tb=long
```

---

## Full Deployment Validation Sequence

Run this end-to-end before any production deployment:

```bash
# ── Stage 1: Python backend unit tests (must all pass) ────────────────────
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/unit/test_subscription_repository.py \
              tests/unit/test_billing_service.py \
              tests/unit/test_webhook_service.py \
              tests/unit/test_quota_service.py \
              -v --tb=short

# ── Stage 2: TypeScript happy-path (must all pass) ────────────────────────
cd /Users/yitzchak/Documents/dev/careervp/src/frontend
npm run test:unit
npm run test:integration
npm run test:regression
npm run test:coverage          # verify >80%

# ── Stage 3: Critical hardening (must all pass) ───────────────────────────
npm run test:critical
npm run test:security

# ── Stage 4: E2E (requires payment provider CLI or relay) ─────────────────
# Start webhook relay in separate terminal, then:
npm run test:e2e

# ── Stage 5: Optional (manual triggers) ───────────────────────────────────
PERF_TEST=true npm run test:perf
OPS_TEST=true  npm run test:ops
```

### Success Criteria

| Check | Target |
|-------|--------|
| Python backend unit tests | All pass |
| TypeScript happy-path tests | 129/129 pass |
| TypeScript critical tests | ~120/120 pass (after hardening) |
| TypeScript security tests | 2/2 pass |
| Code coverage | >80% billing module |
| Python lint | 0 errors (`uv run ruff check careervp`) |
| Python type check | 0 errors (`uv run mypy careervp --strict`) |
| CloudWatch post-deploy | Zero new errors for 30 min |

---

## Test Count Summary

| Suite | Language | Files | ~Cases | Command |
|-------|----------|-------|--------|---------|
| Subscription DAL | Python | 1 | ~40 | `pytest test_subscription_repository.py` |
| Billing service | Python | 1 | ~30 | `pytest test_billing_service.py` |
| Webhook service | Python | 1 | ~35 | `pytest test_webhook_service.py` |
| Quota service | Python | 1 | ~15 | `pytest test_quota_service.py` |
| Unit (happy-path) | TypeScript | 13 | 82 | `test:unit` |
| Integration (happy-path) | TypeScript | 3 | 11 | `test:integration` |
| E2E | TypeScript | 5 | 10 | `test:e2e` |
| Regression | TypeScript | 7 | 26 | `test:regression` |
| Unit (critical) | TypeScript | 8 | ~40 | `test:critical` |
| Integration (critical) | TypeScript | 14 | ~56 | `test:critical` |
| Performance | TypeScript | 2 | ~8 | `PERF_TEST=true test:perf` |
| Ops | TypeScript | 6 | ~18 | `OPS_TEST=true test:ops` |
| Security | TypeScript | 2 | ~8 | `test:security` |
| **TOTAL** | | **64** | **~379** | |
