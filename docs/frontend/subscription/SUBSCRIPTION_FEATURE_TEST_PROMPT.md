# Subscription Service — Feature & Test Extraction Prompt

**Purpose:** This prompt instructs an AI agent to extract subscription feature sets from the source specification documents, explain each feature in plain terms, and define a corresponding feature test with AWS infrastructure context.

**Output audience:** Backend developers, QA engineers, and AI code generation agents.

**Source documents:**

- `docs/frontend/SUBSCRIPTION_STRIPE_SPEC.md` — Backend spec (Stripe, DynamoDB, Lambda, webhooks)

- `docs/frontend/FRONTEND_ARCHITECTURE.md` — Frontend stack and Stripe integration sections

- `docs/frontend/MASTER_TASK_LIST.md` — Task tracking, phases S-001–S-015 and B-001–B-014

---

## Domain Definitions

| Term | Definition |

| --- | --- |

| **Application** | A single job application workflow. An application is created when the user generates a Gap Analysis question set for a job. |

| **Trial** | 14-day free period starting at `created_at`. Includes 3 application credits. |

| **Credit** | One application creation right. Consumed when a Gap Analysis question set is generated. |

| **Subscription** | Active Stripe subscription; grants unlimited applications. Plans: Monthly ($29) or Quarterly ($75). |

| **Expired trial** | Trial window has closed (`now > created_at + 14 days`). User can continue using existing 3 applications but cannot create new ones. |

---

## File Conventions

| Artifact | Location | Naming |

| --- | --- | --- |

| Test payloads (JSON fixtures) | `src/frontend/tests/payloads/` | `{feature}-{scenario}.json` |

| Unit tests | `src/frontend/tests/unit/` | `{feature}.test.ts` |

| Integration tests | `src/frontend/tests/integration/` | `{feature}.integration.test.ts` |

| E2E tests | `src/frontend/tests/e2e/` | `{feature}.e2e.test.ts` |

| Regression tests | `src/frontend/tests/regression/` | `{feature}.regression.test.ts` |

All test files reference payloads via relative import: `../../payloads/{file}.json`.

---

## Entry Format

Each feature below follows this structure:

```

## Feature: <Name>

### What it does
<1–3 sentence plain-language description — user perspective and system perspective.>

### AWS Resources Involved

| Resource | Role |

| --- | --- |

| <service> | <what it does in this feature> |

### Tests

#### Unit — <Test ID>
**File:** src/frontend/tests/unit/<feature>.test.ts
**Payload:** src/frontend/tests/payloads/<feature>-<scenario>.json
**Preconditions:** ...
**Steps:** ...
**Expected Result:** ...

#### Integration — <Test ID>
...

#### E2E — <Test ID>
...

#### Regression — <Test ID>
...

```

Not every feature requires all four types. Include only the types that are meaningful for the feature.

---

## Features

---

### 1. Trial Activation on Sign-Up

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §1, §3

When a new user registers, a 14-day free trial with 3 application credits begins implicitly. No subscription record is created yet — trial state is derived from `created_at` on the user record and the `remaining` credit count on the usage record.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| Cognito User Pool (`us-east-1_WiHMRqLpe`) | Identity source; `sub` UUID becomes `user_id` |

| DynamoDB `careervp-users-{stage}` | Stores `created_at`; basis for trial expiry calculation |

| DynamoDB `careervp-usage-{stage}` | Stores `remaining = 3` on signup |

| Lambda `careervp-billing-{stage}` | Reads both tables in `_check_trial_and_quota()` |

#### Unit — F-SUB-001

**File:** `src/frontend/tests/unit/trial.test.ts`
**Payload:** `src/frontend/tests/payloads/trial-active.json`

```json
// trial-active.json
{
  "user": { "user_id": "user-001", "created_at": "<NOW_MINUS_2_DAYS>" },
  "usage": { "user_id": "user-001", "remaining": 3 },
  "subscription": null
}

```

**Preconditions:** User `created_at` = 2 days ago; `remaining = 3`; no subscription record
**Steps:**

1. Call `_check_trial_and_quota("user-001")` with mocked DynamoDB returning payload

2. Assert no exception raised

**Expected Result:** Access granted; no error thrown

**AWS Verification:** No DynamoDB write; CloudWatch shows no error

---

### 2. Trial Expiry — Access Blocked After 14 Days

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §3, §9

If `created_at` is more than 14 days ago and no active subscription exists, job creation is blocked. Existing applications remain accessible — only new application creation is blocked.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| DynamoDB `careervp-users-{stage}` | `created_at` source |

| DynamoDB `careervp-subscriptions-{stage}` | Checked via `UserSubscriptionIndex` GSI |

| Lambda `careervp-billing-{stage}` | Enforces `_check_trial_and_quota()` |

| API Gateway `POST /jobs` | Returns 403 |

#### Unit — F-SUB-002

**File:** `src/frontend/tests/unit/trial.test.ts`
**Payload:** `src/frontend/tests/payloads/trial-expired.json`

```json
// trial-expired.json
{
  "user": { "user_id": "user-002", "created_at": "<NOW_MINUS_15_DAYS>" },
  "usage": { "user_id": "user-002", "remaining": 1 },
  "subscription": null
}

```

**Preconditions:** `created_at` = 15 days ago; `remaining = 1` (credits available, expiry takes precedence); no subscription
**Steps:**

1. Call `_check_trial_and_quota("user-002")`

2. Assert `ApiError(403, { "error": "trial_expired" })`

**Expected Result:** 403 `trial_expired`

#### Regression — F-SUB-002-R

**File:** `src/frontend/tests/regression/trial-expiry-boundary.regression.test.ts`
**Description:** Confirm the boundary is exactly 14 days (not 13, not 15).

**Cases:**

| `created_at` offset | Expected |

| --- | --- |

| -13 days 23 hours | Access granted |

| -14 days exactly | Blocked (`trial_expired`) |

| -15 days | Blocked (`trial_expired`) |

**AWS Verification:** CloudWatch log contains `trial_expired` for blocked cases; no log for allowed case

---

### 3. Trial Credits Exhausted

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §3, §9

Within the 14-day window, if the user has consumed all 3 application credits, new application creation is blocked with `trial_exhausted`. Existing applications remain accessible.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| DynamoDB `careervp-usage-{stage}` | `remaining = 0` |

| Lambda `careervp-billing-{stage}` | Credit check in `_check_trial_and_quota()` |

| API Gateway `POST /jobs` | Returns 403 |

#### Unit — F-SUB-003

**File:** `src/frontend/tests/unit/trial.test.ts`
**Payload:** `src/frontend/tests/payloads/trial-exhausted.json`

```json
// trial-exhausted.json
{
  "user": { "user_id": "user-003", "created_at": "<NOW_MINUS_2_DAYS>" },
  "usage": { "user_id": "user-003", "remaining": 0 },
  "subscription": null
}

```

**Preconditions:** `created_at` = 2 days ago (within trial); `remaining = 0`
**Steps:**

1. Call `_check_trial_and_quota("user-003")`

2. Assert `ApiError(403, { "error": "trial_exhausted" })`

**Expected Result:** 403 `trial_exhausted`

#### Regression — F-SUB-003-R

**File:** `src/frontend/tests/regression/trial-exhausted-boundary.regression.test.ts`

**Cases:**

| `remaining` | Expected |

| --- | --- |

| 1 | Access granted |

| 0 | Blocked (`trial_exhausted`) |

| -1 (invalid, guard) | Blocked (`trial_exhausted`) |

---

### 4. Checkout Session Creation

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §5.1, §6

An authenticated user initiates upgrade. The backend resolves or creates a Stripe Customer, maps the plan to a price ID (`monthly` → `STRIPE_PRICE_MONTHLY`, `quarterly` → `STRIPE_PRICE_QUARTERLY`), calls `stripe.checkout.Session.create()`, and returns the hosted payment URL.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| Cognito User Pool | JWT validated via `get_user_id_from_event()` |

| API Gateway `POST /billing/checkout` | Cognito-protected route |

| Lambda `careervp-billing-{stage}` | Calls Stripe API; writes `stripe_customer_id` |

| DynamoDB `careervp-users-{stage}` | `stripe_customer_id` stored post-customer-creation |

| DynamoDB `careervp-subscriptions-{stage}` | Checked for existing active sub (prevents duplicate) |

| SSM Parameter Store | `STRIPE_SECRET_KEY`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_QUARTERLY` |

#### Unit — F-SUB-004

**File:** `src/frontend/tests/unit/checkout.test.ts`
**Payload:** `src/frontend/tests/payloads/checkout-monthly-request.json`

```json
// checkout-monthly-request.json
{
  "plan": "monthly",
  "success_url": "https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://app.careervp.com/settings/billing"
}

```

**Preconditions:**

- Valid Cognito JWT for `user-004`

- No active subscription record

- No existing `stripe_customer_id`

- Stripe mock: `Customer.create()` → `cus_test001`; `checkout.Session.create()` → `{ url: "https://checkout.stripe.com/..." }`

**Steps:**

1. POST `/billing/checkout` with payload

2. Assert `stripe.Customer.create()` called with `metadata.user_id = "user-004"`

3. Assert `dal.store_customer_id("user-004", "cus_test001")` called

4. Assert response `200` with `{ "checkout_url": "https://checkout.stripe.com/..." }`

**Expected Result:** 200 with `checkout_url`

#### Unit — F-SUB-004b (Quarterly plan)

**Payload:** `src/frontend/tests/payloads/checkout-quarterly-request.json`

```json
// checkout-quarterly-request.json
{
  "plan": "quarterly",
  "success_url": "https://app.careervp.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
  "cancel_url": "https://app.careervp.com/settings/billing"
}

```

**Steps:**

1. POST `/billing/checkout` with quarterly payload

2. Assert `stripe.checkout.Session.create()` called with `STRIPE_PRICE_QUARTERLY`

#### Unit — F-SUB-004c (Invalid plan → 400)

**Payload:** `src/frontend/tests/payloads/checkout-invalid-plan.json`

```json
// checkout-invalid-plan.json
{ "plan": "annual", "success_url": "...", "cancel_url": "..." }

```

**Steps:**

1. POST `/billing/checkout` with `plan = "annual"`

2. Assert response `400` with message about invalid plan

#### Integration — F-SUB-004-INT

**File:** `src/frontend/tests/integration/checkout.integration.test.ts`
**Environment:** `dev` stage; Stripe test mode

**Steps:**

1. POST `/billing/checkout` with a real Cognito JWT (test user)

2. Assert `200` response and `checkout_url` begins with `https://checkout.stripe.com/`

3. Assert DynamoDB `careervp-users-dev` item for test user has `stripe_customer_id` set

**AWS Verification:** DynamoDB write confirmed; CloudWatch: `Checkout session created for user`

---

### 5. Stripe Customer Reuse on Re-Subscribe

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §5.1 — `get_customer_id()` fallback logic

If a user previously subscribed (or started checkout), they already have a `stripe_customer_id`. On re-subscribe, the backend must reuse the existing customer rather than creating a duplicate Stripe Customer record.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| DynamoDB `careervp-users-{stage}` | `stripe_customer_id` field checked before creating new customer |

| DynamoDB `careervp-subscriptions-{stage}` | `CustomerIndex` GSI also checked as fallback |

| Lambda `careervp-billing-{stage}` | `dal.get_customer_id()` handles both lookups |

| Stripe | No duplicate `Customer.create()` call |

#### Unit — F-SUB-005

**File:** `src/frontend/tests/unit/checkout.test.ts`
**Payload:** `src/frontend/tests/payloads/checkout-existing-customer.json`

```json
// checkout-existing-customer.json
{
  "user": { "user_id": "user-005", "stripe_customer_id": "cus_existing001" },
  "subscription": null
}

```

**Steps:**

1. POST `/billing/checkout` with valid body

2. Assert `stripe.Customer.create()` is NOT called

3. Assert `stripe.checkout.Session.create()` called with `customer = "cus_existing001"`

**Expected Result:** 200 with `checkout_url`; no new Stripe customer created

#### Regression — F-SUB-005-R

**File:** `src/frontend/tests/regression/customer-dedup.regression.test.ts`
**Description:** Simulate the full path: initial checkout → canceled → re-checkout. Confirm only 1 Stripe customer exists for the user.

---

### 6. Duplicate Checkout Blocked

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §5.1

If a user already has an `active` subscription and attempts checkout, the endpoint returns `409` without calling Stripe.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| DynamoDB `careervp-subscriptions-{stage}` | `UserSubscriptionIndex` GSI query detects active sub |

| Lambda `careervp-billing-{stage}` | Returns 409 before Stripe call |

#### Unit — F-SUB-006

**File:** `src/frontend/tests/unit/checkout.test.ts`
**Payload:** `src/frontend/tests/payloads/checkout-already-active.json`

```json
// checkout-already-active.json
{
  "subscription": {
    "subscription_id": "sub_active001",
    "user_id": "user-006",
    "status": "active",
    "plan": "monthly"
  }
}

```

**Steps:**

1. POST `/billing/checkout` with valid body

2. Assert `stripe.checkout.Session.create()` NOT called

3. Assert response `409` with `User already has an active subscription`

**Expected Result:** 409; no Stripe API call

---

### 7. Customer Portal Session

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §5.2

Authenticated paying users access the Stripe Customer Portal to manage their subscription (cancel, update card, view invoices). The backend looks up the `customer_id` and returns a short-lived portal URL.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| Cognito User Pool | JWT required |

| API Gateway `POST /billing/portal` | Cognito-protected route |

| Lambda `careervp-billing-{stage}` | Calls `stripe.billing_portal.Session.create()` |

| DynamoDB `careervp-subscriptions-{stage}` | `CustomerIndex` GSI for `customer_id` lookup |

#### Unit — F-SUB-007

**File:** `src/frontend/tests/unit/portal.test.ts`
**Payload:** `src/frontend/tests/payloads/portal-request.json`

```json
// portal-request.json
{
  "return_url": "https://app.careervp.com/settings/billing",
  "customer_id": "cus_Nabc"
}

```

**Steps:**

1. POST `/billing/portal` with `{ "return_url": "..." }`; DynamoDB mock returns `customer_id = "cus_Nabc"`

2. Assert `stripe.billing_portal.Session.create()` called with `customer = "cus_Nabc"`

3. Assert response `200` with `{ "portal_url": "https://billing.stripe.com/..." }`

#### Unit — F-SUB-007b (No customer → 404)

**Payload:** `src/frontend/tests/payloads/portal-no-customer.json`

```json
// portal-no-customer.json
{ "user": { "user_id": "user-007b" }, "subscription": null }

```

**Steps:**

1. POST `/billing/portal`; DynamoDB returns no `customer_id`

2. Assert response `404` with `No billing account found`

---

### 8. Get Subscription Status

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §5.3

Authenticated users can query their current subscription. Returns state, plan, billing period end, trial end, and `has_active_subscription` boolean. Returns `null` when no subscription exists.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| Cognito User Pool | JWT required |

| API Gateway `GET /users/me/subscription` | Cognito-protected route |

| Lambda `careervp-billing-{stage}` | DynamoDB read + response shaping |

| DynamoDB `careervp-subscriptions-{stage}` | `UserSubscriptionIndex` GSI lookup |

#### Unit — F-SUB-008

**File:** `src/frontend/tests/unit/subscription-status.test.ts`
**Payload:** `src/frontend/tests/payloads/subscription-active.json`

```json
// subscription-active.json
{
  "subscription_id": "sub_1Pxyz",
  "customer_id": "cus_Nabc",
  "status": "active",
  "plan": "monthly",
  "current_period_end": "2026-04-14T00:00:00Z",
  "cancel_at_period_end": false,
  "trial_end": null
}

```

**Steps:**

1. GET `/users/me/subscription`; DynamoDB mock returns payload

2. Assert `200` with `has_active_subscription = true`

3. Assert all payload fields present in response

#### Unit — F-SUB-008b (No subscription → null)

**Steps:**

1. GET `/users/me/subscription`; DynamoDB returns empty

2. Assert `200` with `{ "subscription": null, "has_active_subscription": false }`

#### Regression — F-SUB-008-R

**File:** `src/frontend/tests/regression/subscription-status-shapes.regression.test.ts`
**Description:** For each possible status value (`trialing`, `active`, `past_due`, `canceled`, `expired`), assert the response shape is valid and `has_active_subscription` is correctly `true` only for `active`.

| Status | `has_active_subscription` |

| --- | --- |

| `trialing` | `false` |

| `active` | `true` |

| `past_due` | `false` |

| `canceled` | `false` |

| `expired` | `false` |

---

### 9. Webhook — Signature Verification

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §5.4, §7

The `/billing/webhook` route has **no Cognito authorizer**. All security relies on Stripe webhook signature verification via `STRIPE_WEBHOOK_SECRET`. A missing or invalid signature must return `400` with zero DynamoDB side effects. API Gateway must pass the **raw body bytes** to Lambda unchanged — any body transformation breaks the signature hash.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway `POST /billing/webhook` | No Cognito auth; raw body passthrough required |

| Lambda `careervp-billing-{stage}` | `stripe.Webhook.construct_event()` signature check |

| SSM Parameter Store | `STRIPE_WEBHOOK_SECRET` read at init |

#### Unit — F-SUB-009

**File:** `src/frontend/tests/unit/webhook-signature.test.ts`
**Payload:** `src/frontend/tests/payloads/webhook-invalid-signature.json`

```json
// webhook-invalid-signature.json
{
  "headers": { "Stripe-Signature": "t=1234567890,v1=badhash" },
  "body": "{\"type\":\"checkout.session.completed\",\"data\":{}}"
}

```

**Steps:**

1. POST `/billing/webhook` with invalid signature header

2. Assert response `400` with `Invalid signature`

3. Assert `dal.upsert_subscription()` NOT called

4. Assert `dal.update_subscription_fields()` NOT called

**Expected Result:** 400; zero DynamoDB writes

#### Integration — F-SUB-009-INT (Raw body passthrough)

**File:** `src/frontend/tests/integration/webhook-rawbody.integration.test.ts`
**Description:** Verify API Gateway is configured with `contentHandling: CONVERT_TO_TEXT` and does not modify the request body before forwarding to Lambda.

**Steps:**

1. Use Stripe CLI: `stripe listen --forward-to https://dev-api.careervp.com/billing/webhook`

2. Send `stripe trigger checkout.session.completed`

3. Assert Lambda CloudWatch log shows successful signature verification (no `SignatureVerificationError`)

**AWS Verification:** CloudWatch: no `Stripe signature verification failed`; CDK template has no `requestModels` body transform on webhook route

---

### 10. Webhook — Checkout Completed (Subscription Activated)

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §7

When Stripe fires `checkout.session.completed`, the handler creates the subscription record with `status = "active"`, stores billing period dates from the full Stripe subscription object, and sets usage `remaining = 9999` to signal unlimited access.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway `POST /billing/webhook` | Public, no auth; raw body |

| Lambda `careervp-billing-{stage}` | Processes event, calls `upsert_subscription()` + `set_unlimited_usage()` |

| DynamoDB `careervp-subscriptions-{stage}` | New subscription item written |

| DynamoDB `careervp-usage-{stage}` | `remaining` set to 9999 |

| SSM Parameter Store | `STRIPE_WEBHOOK_SECRET` for verification |

#### Unit — F-SUB-010

**File:** `src/frontend/tests/unit/webhook-checkout.test.ts`
**Payload:** `src/frontend/tests/payloads/webhook-checkout-completed.json`

```json
// webhook-checkout-completed.json
{
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_test_001",
      "subscription": "sub_1Pxyz",
      "customer": "cus_Nabc",
      "metadata": { "user_id": "user-010", "plan": "monthly" }
    }
  }
}

```

**Stripe mock:** `stripe.Subscription.retrieve("sub_1Pxyz")` →

```json
{
  "id": "sub_1Pxyz",
  "current_period_start": 1741996800,
  "current_period_end": 1744675200,
  "cancel_at_period_end": false,
  "items": { "data": [{ "price": { "id": "price_monthly_001" } }] }
}

```

**Steps:**

1. POST `/billing/webhook` with signed event

2. Assert `dal.upsert_subscription()` called with `status = "active"`, `plan = "monthly"`

3. Assert `dal.set_unlimited_usage("user-010")` called

4. Assert response `200` `{ "received": true }`

**Expected Result:** 200; subscription active; usage unlimited

#### E2E — F-SUB-010-E2E

**File:** `src/frontend/tests/e2e/checkout-to-active.e2e.test.ts`
**Environment:** `dev` stage; Stripe test mode; Stripe CLI webhook relay

**Steps:**

1. Create test user via Cognito; assert `trialing` state

2. POST `/billing/checkout` with `plan = "monthly"`; follow `checkout_url`

3. Complete checkout with Stripe test card `4242 4242 4242 4242`

4. Wait for webhook delivery (poll or Stripe CLI event log)

5. GET `/users/me/subscription` → assert `status = "active"`

6. POST `/jobs` → assert `200` (not blocked)

**Expected Result:** Full upgrade flow completes; user has unlimited access

**AWS Verification:**

- DynamoDB `careervp-subscriptions-dev`: `status = "active"`, `remaining = 9999`

- CloudWatch: `Subscription activated for user user-010`

---

### 11. Webhook — Idempotency (Duplicate Event Handling)

**Source:** MASTER_TASK_LIST.md P1-005; SUBSCRIPTION_STRIPE_SPEC.md §5.4

Stripe may deliver the same webhook event more than once (network retry, timeout). Processing `checkout.session.completed` twice must not create duplicate records or double-reset usage. The system must handle duplicate events gracefully.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| DynamoDB `careervp-subscriptions-{stage}` | `upsert_subscription()` uses `put_item` — second call overwrites with same data (safe) |

| DynamoDB `careervp-usage-{stage}` | `set_unlimited_usage()` is idempotent (sets to 9999 regardless) |

| Lambda `careervp-billing-{stage}` | Must not throw on duplicate; must return 200 |

#### Unit — F-SUB-011

**File:** `src/frontend/tests/unit/webhook-idempotency.test.ts`
**Payload:** `src/frontend/tests/payloads/webhook-checkout-completed.json` (reuse from F-SUB-010)

**Steps:**

1. POST `/billing/webhook` with `checkout.session.completed` event — first delivery

2. Assert `200` returned; subscription record exists with `status = "active"`

3. POST `/billing/webhook` with identical event — second delivery (same Stripe event ID)

4. Assert `200` returned

5. Assert DynamoDB subscription item is identical to after step 2 (no mutation)

6. Assert `remaining` is still 9999 (no double increment or reset to 3)

**Expected Result:** Both calls return 200; state unchanged after second delivery

#### Regression — F-SUB-011-R

**File:** `src/frontend/tests/regression/webhook-idempotency.regression.test.ts`
**Description:** Replay each of the 5 webhook event types twice. Confirm none causes data corruption.

| Event | Safe on Repeat? |

| --- | --- |

| `checkout.session.completed` | Yes — `put_item` is idempotent |

| `invoice.payment_succeeded` | Yes — sets same `status = "active"`, resets count to 0 |

| `invoice.payment_failed` | Needs care — `attempt_count` from Stripe payload, not local counter |

| `customer.subscription.updated` | Yes — overwrites with same Stripe data |

| `customer.subscription.deleted` | Yes — `status = "canceled"` is terminal |

---

### 12. Webhook — Invoice Payment Succeeded (Recovery)

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §7

When a previously `past_due` user updates their card and payment succeeds, Stripe fires `invoice.payment_succeeded`. The handler resets `payment_failed_count` to 0 and sets `status = "active"`.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway `POST /billing/webhook` | Public, no auth |

| Lambda `careervp-billing-{stage}` | `_handle_invoice_succeeded()` |

| DynamoDB `careervp-subscriptions-{stage}` | `status` → `active`, `payment_failed_count` → 0 |

#### Unit — F-SUB-012

**File:** `src/frontend/tests/unit/webhook-invoice.test.ts`
**Payload:** `src/frontend/tests/payloads/webhook-invoice-succeeded.json`

```json
// webhook-invoice-succeeded.json
{
  "type": "invoice.payment_succeeded",
  "data": {
    "object": {
      "id": "in_recovered001",
      "subscription": "sub_1Pxyz",
      "customer": "cus_Nabc"
    }
  }
}

```

**Preconditions:** DynamoDB mock: subscription exists with `status = "past_due"`, `payment_failed_count = 2`

**Steps:**

1. POST `/billing/webhook` with signed `invoice.payment_succeeded` event

2. Assert `dal.update_subscription_fields()` called with `status = "active"`, `payment_failed_count = 0`, `last_invoice_id = "in_recovered001"`

3. Assert response `200`

**Expected Result:** 200; subscription recovered to `active`

#### E2E — F-SUB-012-E2E

**File:** `src/frontend/tests/e2e/payment-recovery.e2e.test.ts`

**Steps:**

1. Trigger payment failure: `stripe trigger invoice.payment_failed`

2. Assert subscription `status = "past_due"` in DynamoDB

3. Update test card via Customer Portal to `4242 4242 4242 4242`

4. Trigger recovery: `stripe trigger invoice.payment_succeeded`

5. GET `/users/me/subscription` → assert `status = "active"`

---

### 13. Webhook — Payment Failed (Mark Past Due)

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §7

When `invoice.payment_failed` fires, the subscription is marked `past_due` and `payment_failed_count` is incremented. After the 3rd failure, Stripe cancels the subscription separately via `customer.subscription.deleted`.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway `POST /billing/webhook` | Public, no auth |

| Lambda `careervp-billing-{stage}` | `_handle_invoice_failed()` |

| DynamoDB `careervp-subscriptions-{stage}` | `status = "past_due"`, `payment_failed_count` incremented |

#### Unit — F-SUB-013

**File:** `src/frontend/tests/unit/webhook-invoice.test.ts`
**Payload:** `src/frontend/tests/payloads/webhook-invoice-failed.json`

```json
// webhook-invoice-failed.json
{
  "type": "invoice.payment_failed",
  "data": {
    "object": {
      "id": "in_fail001",
      "subscription": "sub_1Pxyz",
      "customer": "cus_Nabc",
      "attempt_count": 1
    }
  }
}

```

**Steps:**

1. POST `/billing/webhook` with signed event

2. Assert `dal.update_subscription_fields()` called with `status = "past_due"`, `payment_failed_count = 1`

3. Assert response `200`

#### E2E — F-SUB-013-E2E

**File:** `src/frontend/tests/e2e/payment-failure-banner.e2e.test.ts`

**Steps:**

1. `stripe trigger invoice.payment_failed`

2. Wait for webhook

3. Reload app; assert `past_due` banner visible

4. Attempt to create a job → assert `403 subscription_required`

---

### 14. Webhook — Subscription Updated (Plan Change / Cancel Toggle)

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §7 `_handle_subscription_updated()`

When Stripe fires `customer.subscription.updated`, the handler syncs key fields: `status`, `plan`, `price_id`, billing period dates, and `cancel_at_period_end`. This covers plan changes (monthly ↔ quarterly) and the user toggling "cancel at period end" from the portal.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway `POST /billing/webhook` | Public, no auth |

| Lambda `careervp-billing-{stage}` | `_handle_subscription_updated()` |

| DynamoDB `careervp-subscriptions-{stage}` | Multiple fields updated |

#### Unit — F-SUB-014a (Plan change)

**File:** `src/frontend/tests/unit/webhook-subscription-updated.test.ts`
**Payload:** `src/frontend/tests/payloads/webhook-subscription-updated-plan-change.json`

```json
// webhook-subscription-updated-plan-change.json
{
  "type": "customer.subscription.updated",
  "data": {
    "object": {
      "id": "sub_1Pxyz",
      "status": "active",
      "cancel_at_period_end": false,
      "current_period_start": 1741996800,
      "current_period_end": 1752192000,
      "items": {
        "data": [{ "price": { "id": "<STRIPE_PRICE_QUARTERLY>" } }]
      }
    }
  }
}

```

**Preconditions:** DynamoDB mock: subscription exists with `plan = "monthly"`

**Steps:**

1. POST `/billing/webhook` with signed event

2. Assert `dal.update_subscription_fields()` called with `plan = "quarterly"`

3. Assert response `200`

#### Unit — F-SUB-014b (Cancel at period end toggled)

**Payload:** `src/frontend/tests/payloads/webhook-subscription-cancel-scheduled.json`

```json
// webhook-subscription-cancel-scheduled.json
{
  "type": "customer.subscription.updated",
  "data": {
    "object": {
      "id": "sub_1Pxyz",
      "status": "active",
      "cancel_at_period_end": true,
      "current_period_start": 1741996800,
      "current_period_end": 1744675200,
      "items": {
        "data": [{ "price": { "id": "<STRIPE_PRICE_MONTHLY>" } }]
      }
    }
  }
}

```

**Steps:**

1. POST `/billing/webhook` with signed event

2. Assert `dal.update_subscription_fields()` called with `cancel_at_period_end = true`, `status = "active"`

3. Assert response `200`

---

### 15. Cancel-at-Period-End UX Distinction

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §3, §7; FRONTEND_ARCHITECTURE.md §18

When a user cancels via the portal, Stripe sets `cancel_at_period_end = true` — the subscription stays `active` until the period ends, then fires `customer.subscription.deleted`. The frontend must distinguish this "active but canceling" state from "active and renewing" and show the appropriate UI (e.g. "Cancels on Apr 14, 2026" vs "Renews Apr 14, 2026").

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| DynamoDB `careervp-subscriptions-{stage}` | `cancel_at_period_end = true`, `status = "active"` |

| API Gateway `GET /users/me/subscription` | Returns both fields to frontend |

| Frontend `useSubscription` hook | Must expose `isCancelingAtPeriodEnd` derived state |

#### Unit — F-SUB-015

**File:** `src/frontend/tests/unit/subscription-status.test.ts`
**Payload:** `src/frontend/tests/payloads/subscription-canceling.json`

```json
// subscription-canceling.json
{
  "subscription_id": "sub_1Pxyz",
  "status": "active",
  "plan": "monthly",
  "current_period_end": "2026-04-14T00:00:00Z",
  "cancel_at_period_end": true,
  "trial_end": null
}

```

**Steps:**

1. Call `useSubscription()` hook with above payload

2. Assert `isActive = true`

3. Assert `isCancelingAtPeriodEnd = true`

4. Assert billing page renders "Cancels on Apr 14, 2026" (not "Renews")

**Expected Result:** Correct label; no access block while still within the period

#### Regression — F-SUB-015-R

**File:** `src/frontend/tests/regression/cancel-at-period-end.regression.test.ts`

**Cases:**

| `cancel_at_period_end` | `status` | Expected label |

| --- | --- | --- |

| `false` | `active` | "Renews Apr 14, 2026" |

| `true` | `active` | "Cancels Apr 14, 2026" |

| `false` | `canceled` | "Canceled" |

---

### 16. Webhook — Subscription Canceled

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §7

When Stripe fires `customer.subscription.deleted` (user cancels via portal or Stripe cancels after max failures), the handler sets `status = "canceled"` and records `canceled_at`. The user is blocked from creating jobs at their next API call.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway `POST /billing/webhook` | Public, no auth |

| Lambda `careervp-billing-{stage}` | `_handle_subscription_deleted()` |

| DynamoDB `careervp-subscriptions-{stage}` | `status = "canceled"`, `canceled_at` written |

#### Unit — F-SUB-016

**File:** `src/frontend/tests/unit/webhook-subscription-deleted.test.ts`
**Payload:** `src/frontend/tests/payloads/webhook-subscription-deleted.json`

```json
// webhook-subscription-deleted.json
{
  "type": "customer.subscription.deleted",
  "data": {
    "object": { "id": "sub_1Pxyz" }
  }
}

```

**Steps:**

1. POST `/billing/webhook` with signed event

2. Assert `dal.update_subscription_fields()` called with `status = "canceled"`, `cancel_at_period_end = false`, and `canceled_at` is an ISO timestamp

3. Assert response `200`

#### E2E — F-SUB-016-E2E

**File:** `src/frontend/tests/e2e/subscription-cancel.e2e.test.ts`

**Steps:**

1. `stripe trigger customer.subscription.deleted`

2. GET `/users/me/subscription` → assert `status = "canceled"`

3. POST `/jobs` → assert `403 subscription_required`

---

### 17. Quota Enforcement — Blocked States

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §9

Users with `status` of `past_due`, `canceled`, or `expired` must be blocked from creating new applications. The check fires at the top of `POST /jobs` before any AI processing.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway `POST /jobs` | Returns 403 |

| Lambda job handler | `_check_trial_and_quota()` at function entry |

| DynamoDB `careervp-subscriptions-{stage}` | `UserSubscriptionIndex` GSI read |

#### Unit — F-SUB-017 (Parametrized)

**File:** `src/frontend/tests/unit/quota-enforcement.test.ts`
**Payloads:**

- `src/frontend/tests/payloads/subscription-past-due.json`

- `src/frontend/tests/payloads/subscription-canceled.json`

- `src/frontend/tests/payloads/subscription-expired.json`

```json
// subscription-past-due.json
{ "subscription_id": "sub_1Pxyz", "user_id": "user-017", "status": "past_due" }

```

**Steps (run for each status):**

1. Set DynamoDB mock to return subscription with that status

2. Call `_check_trial_and_quota(user_id)`

3. Assert `ApiError(403, { "error": "subscription_required" })`

**Expected Result:** 403 for all three blocked statuses

#### Regression — F-SUB-017-R

**File:** `src/frontend/tests/regression/quota-all-states.regression.test.ts`

| Status | `_check_trial_and_quota` result |

| --- | --- |

| `active` | Pass (no exception) |

| `trialing` + credits > 0 | Pass |

| `trialing` + credits = 0 | Raise `trial_exhausted` |

| `past_due` | Raise `subscription_required` |

| `canceled` | Raise `subscription_required` |

| `expired` | Raise `subscription_required` |

| No subscription + trial active | Pass |

| No subscription + trial expired | Raise `trial_expired` |

---

### 18. CDK Infrastructure Provisioning

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §10

The CDK stack must provision: the subscriptions DynamoDB table with 3 GSIs, the billing Lambda with correct memory/timeout/env vars, APIGW routes (with and without Cognito authorizer), IAM grants, and SSM parameter references for all Stripe secrets.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| CDK `aws_dynamodb.Table` | `careervp-subscriptions-{stage}`; PK `subscription_id` |

| DynamoDB GSI `UserSubscriptionIndex` | PK: `user_id`, SK: `created_at` |

| DynamoDB GSI `StatusIndex` | PK: `status`, SK: `user_id` |

| DynamoDB GSI `CustomerIndex` | PK: `customer_id` |

| Lambda `careervp-billing-{stage}` | 256 MB, 30s timeout; env vars from SSM |

| IAM | `ReadWriteData` on subscriptions, users, and usage tables |

| API Gateway | `/billing/checkout` + `/billing/portal` → Cognito auth; `/billing/webhook` → no auth |

| SSM Parameter Store | `STRIPE_SECRET_KEY` (SecureString), `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_QUARTERLY` (String) |

#### Unit — F-SUB-018 (CDK Snapshot)

**File:** `src/frontend/tests/unit/cdk-infra.test.ts`

**Steps:**

1. Run `cd infra && cdk synth`

2. Parse generated CloudFormation template

3. Assert table `careervp-subscriptions-dev` exists with PK `subscription_id`

4. Assert 3 GSIs present with correct key schemas

5. Assert Lambda `MemorySize: 256`, `Timeout: 30`

6. Assert APIGW method `POST /billing/webhook` has no `AuthorizationType` set

7. Assert APIGW methods `POST /billing/checkout` and `POST /billing/portal` have Cognito authorizer

8. Assert env var `STRIPE_PRICE_QUARTERLY` present (not `STRIPE_PRICE_ANNUAL`)

**Expected Result:** `cdk synth` exits 0; all assertions pass

#### Integration — F-SUB-018-INT

**File:** `src/frontend/tests/integration/cdk-deploy.integration.test.ts`

**Steps:**

1. `cdk deploy --require-approval never --context stage=dev`

2. Verify with AWS CLI:
   - `aws dynamodb describe-table --table-name careervp-subscriptions-dev` → 3 GSIs
   - `aws lambda get-function --function-name careervp-billing-dev` → correct config
   - `aws apigateway get-resources` → webhook route has no authorizer

---

### 19. SSM Cold Start Failure Handling

**Source:** SUBSCRIPTION_STRIPE_SPEC.md §10 — `StringParameter.from_secure_string_parameter_attributes`

If the Lambda cannot read SSM parameters at init time (missing secret, wrong ARN, IAM misconfiguration), it must fail with a clear error logged to CloudWatch rather than silently serving broken responses.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| Lambda `careervp-billing-{stage}` | Reads SSM at module init via env vars |

| SSM Parameter Store | `STRIPE_SECRET_KEY`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_QUARTERLY`, `STRIPE_WEBHOOK_SECRET` |

| IAM | Lambda execution role must have `ssm:GetParameter` on the secret paths |

| CloudWatch | Must log the failure with parameter name |

#### Unit — F-SUB-019

**File:** `src/frontend/tests/unit/lambda-init.test.ts`

**Steps:**

1. Mock `os.environ` with `STRIPE_SECRET_KEY` missing

2. Import (or reload) `billing_handler`

3. Assert `KeyError` or equivalent is raised at module load with a message identifying the missing variable

4. Assert no Stripe API call is attempted

**Expected Result:** Lambda fails fast with a clear diagnostic; does not serve requests with `None` Stripe key

#### Regression — F-SUB-019-R

**File:** `src/frontend/tests/regression/env-var-coverage.regression.test.ts`
**Description:** Assert all required env vars are present in the CDK template for the billing Lambda.

Required vars: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_QUARTERLY`, `STRIPE_WEBHOOK_SECRET`, `SUBSCRIPTIONS_TABLE_NAME`, `USERS_TABLE_NAME`, `USAGE_TABLE_NAME`

---

### 20. CORS on Webhook Route

**Source:** FRONTEND_ARCHITECTURE.md §13; MASTER_TASK_LIST.md C-001, C-002

The `/billing/webhook` route is public and called directly by Stripe (not from a browser). It must not accidentally expose CORS headers that could be exploited, and must not be blocked by CORS misconfiguration. The Cognito-protected billing routes must only allow `https://app.careervp.com` in the `Access-Control-Allow-Origin` header.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| API Gateway | CORS response headers on OPTIONS and error responses |

| Lambda `careervp-billing-{stage}` | `ALLOWED_ORIGINS` env var enforced in response builder |

| CDK `_add_gateway_error_responses()` | Must not set `'*'` on error responses |

#### Unit — F-SUB-020

**File:** `src/frontend/tests/unit/cors.test.ts`

**Steps:**

1. Send OPTIONS preflight to `/billing/checkout` with `Origin: https://app.careervp.com`

2. Assert `Access-Control-Allow-Origin: https://app.careervp.com`

3. Send OPTIONS with `Origin: https://evil.example.com`

4. Assert `Access-Control-Allow-Origin` is NOT `https://evil.example.com` and NOT `*`

#### Regression — F-SUB-020-R

**File:** `src/frontend/tests/regression/cors-no-wildcard.regression.test.ts`
**Description:** Grep CDK source and Lambda response builder for any `'*'` in CORS origin config; assert none found outside test environments.

---

### 21. Frontend — Upgrade Flow (Full E2E)

**Source:** MASTER_TASK_LIST.md B-001–B-014; FRONTEND_ARCHITECTURE.md §18

The complete user-facing upgrade path: trial prompt → PlanCard selection → CheckoutButton redirect → Stripe Checkout → success page → subscription status refreshed in UI. Covers both Monthly ($29) and Quarterly ($75) paths.

**AWS Resources Involved:**

| Resource | Role |

| --- | --- |

| Cognito User Pool | JWT for all API calls |

| API Gateway `POST /billing/checkout` | Returns `checkout_url` |

| Stripe Hosted Checkout | Test card `4242 4242 4242 4242` |

| API Gateway `POST /billing/webhook` | `checkout.session.completed` from Stripe |

| Lambda `careervp-billing-{stage}` | Processes webhook |

| DynamoDB `careervp-subscriptions-{stage}` | Subscription record created |

| API Gateway `GET /users/me/subscription` | Polled by `useSubscription` after redirect |

#### E2E — F-SUB-021

**File:** `src/frontend/tests/e2e/upgrade-flow.e2e.test.ts`
**Environment:** `dev` stage; Stripe test mode; Stripe CLI webhook relay

**Steps:**

1. Sign in as test user (`trialing`, credits exhausted)

2. Attempt job creation → `UpgradeModal` appears

3. Select Monthly plan → click `CheckoutButton`

4. Complete Stripe Checkout with `4242 4242 4242 4242`, exp `12/30`, CVC `123`

5. Redirected to `/billing/success?session_id=...`

6. Assert page shows success confirmation

7. GET `/users/me/subscription` → `has_active_subscription = true`

8. POST `/jobs` → `200` (not blocked)

**Expected Result:** Upgrade completes; full access restored

**AWS Verification:**

- DynamoDB `status = "active"`, `remaining = 9999`

- CloudWatch: `Subscription activated for user`

#### Regression — F-SUB-021-R

**File:** `src/frontend/tests/regression/upgrade-quarterly.regression.test.ts`
**Description:** Repeat E2E with Quarterly plan. Assert `plan = "quarterly"` in DynamoDB and `STRIPE_PRICE_QUARTERLY` used in checkout session.

---

## Payload File Index

All payloads live in `src/frontend/tests/payloads/`:

| File | Used by |

| --- | --- |

| `trial-active.json` | F-SUB-001 |

| `trial-expired.json` | F-SUB-002 |

| `trial-exhausted.json` | F-SUB-003 |

| `checkout-monthly-request.json` | F-SUB-004 |

| `checkout-quarterly-request.json` | F-SUB-004b |

| `checkout-invalid-plan.json` | F-SUB-004c |

| `checkout-existing-customer.json` | F-SUB-005 |

| `checkout-already-active.json` | F-SUB-006 |

| `portal-request.json` | F-SUB-007 |

| `portal-no-customer.json` | F-SUB-007b |

| `subscription-active.json` | F-SUB-008 |

| `webhook-invalid-signature.json` | F-SUB-009 |

| `webhook-checkout-completed.json` | F-SUB-010, F-SUB-011 |

| `webhook-invoice-succeeded.json` | F-SUB-012 |

| `webhook-invoice-failed.json` | F-SUB-013 |

| `webhook-subscription-updated-plan-change.json` | F-SUB-014a |

| `webhook-subscription-cancel-scheduled.json` | F-SUB-014b |

| `subscription-canceling.json` | F-SUB-015 |

| `webhook-subscription-deleted.json` | F-SUB-016 |

| `subscription-past-due.json` | F-SUB-017 |

| `subscription-canceled.json` | F-SUB-017 |

| `subscription-expired.json` | F-SUB-017 |

---

## Test Summary

| ID | Feature | Unit | Integration | E2E | Regression |

| --- | --- | :---: | :---: | :---: | :---: |

| F-SUB-001 | Trial activation | ✓ | | | |

| F-SUB-002 | Trial expiry (14d) | ✓ | | | ✓ boundary |

| F-SUB-003 | Credits exhausted | ✓ | | | ✓ boundary |

| F-SUB-004 | Checkout creation (monthly + quarterly) | ✓ | ✓ | | |

| F-SUB-005 | Stripe customer reuse | ✓ | | | ✓ dedup |

| F-SUB-006 | Duplicate checkout blocked | ✓ | | | |

| F-SUB-007 | Customer portal | ✓ | | | |

| F-SUB-008 | Get subscription status | ✓ | | | ✓ all statuses |

| F-SUB-009 | Webhook signature verification | ✓ | ✓ raw body | | |

| F-SUB-010 | Webhook checkout completed | ✓ | | ✓ | |

| F-SUB-011 | Webhook idempotency | ✓ | | | ✓ all events |

| F-SUB-012 | Invoice succeeded (recovery) | ✓ | | ✓ | |

| F-SUB-013 | Invoice failed (past due) | ✓ | | ✓ | |

| F-SUB-014 | Subscription updated webhook | ✓ plan + cancel | | | |

| F-SUB-015 | Cancel-at-period-end UX | ✓ | | | ✓ label variants |

| F-SUB-016 | Subscription canceled webhook | ✓ | | ✓ | |

| F-SUB-017 | Quota enforcement — blocked states | ✓ | | | ✓ all states |

| F-SUB-018 | CDK infrastructure provisioning | ✓ snapshot | ✓ deploy | | |

| F-SUB-019 | SSM cold start failure | ✓ | | | ✓ env var coverage |

| F-SUB-020 | CORS on webhook + billing routes | ✓ | | | ✓ no wildcard |

| F-SUB-021 | Full upgrade flow (monthly + quarterly) | | | ✓ | ✓ quarterly variant |
