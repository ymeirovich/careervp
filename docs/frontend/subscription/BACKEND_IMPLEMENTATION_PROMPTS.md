# Backend Implementation Prompts — Subscription Service

@spec docs/best_practices/yaml/prompt_optimization_spec.yaml
@spec docs/best_practices/yaml/spec_best_practices.yaml
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md
@spec docs/frontend/subscription/TEST_EXECUTION_GUIDE.md

**Spec IDs covered:** S-001 – S-006
**Status:** pending
**Owner:** backend-team
**Updated:** 2026-03-16

Run prompts **in order** — each builds on the previous. Each prompt is paste-ready for an LLM agent.

> **Test philosophy:** Every Python test file (`test_subscription_repository.py`, `test_billing_service.py`,
> `test_webhook_service.py`, `test_quota_service.py`) already exists and defines the expected behaviour.
> Read the relevant test file **before** writing any implementation. The tests are the spec.
> Run both Python and TypeScript tests together per `TEST_EXECUTION_GUIDE.md`.

---

## Quick Reference — Test Groups

| Prompt | Spec | Backend tests | Frontend tests |
|--------|------|---------------|----------------|
| 1 — CDK Infrastructure | S-006 | — | `cdk-infra`, `ssm-cold-start` |
| 2 — SubscriptionRepository | S-002.2, S-004, S-006.3 | `test_subscription_repository` | — |
| 3 — BillingService + handler | S-002, S-003, S-005 | `test_billing_service` | `checkout`, `subscription-status`, `portal`, concurrent/timeout integrations |
| 4 — WebhookService + handler | S-004 | `test_webhook_service` | all `webhook-*`, rawbody/idempotency/partial-failure integrations |
| 5 — QuotaService + Reconciliation | S-001, S-005 | `test_quota_service` | `trial`, `quota-enforcement`, `backward-compat-*`, `lifecycle-*`, state-reconciliation integrations |

**Full regression** (run after all 5 prompts):

```bash
cd src/backend && uv run pytest tests/unit/ -v --tb=short
cd src/frontend && npm run test:unit && npm run test:integration && npm run test:critical
cd infra && cdk synth
grep -r "import stripe" src/backend/careervp/logic/ src/backend/careervp/handlers/ && echo "FAIL" || echo "PASS: no direct stripe imports"
```

---

## Prompt 1 of 5 — CDK Billing Infrastructure (S-006)

**Tests targeted:**
- `src/frontend/tests/unit/cdk-infra.test.ts`
- `src/frontend/tests/unit/ssm-cold-start.test.ts`
- `src/frontend/tests/integration/cdk-deploy.integration.test.ts`

**Pre-check:**
```bash
cd src/frontend && npm run test:unit -- --testPathPattern="cdk-infra|ssm-cold-start" 2>&1 | tail -20
```

---

```
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#infrastructure-s-006
@spec docs/frontend/subscription/TEST_EXECUTION_GUIDE.md#typescript-happy-path-tests
@pattern infra/careervp/*.py

ROLE: AWS CDK Python expert adding billing infrastructure to an existing serverless stack.

PROBLEM: Billing Lambda, EventBridge reconciliation trigger, DLQ alarm, and webhook
raw-body passthrough are all missing. The RestApi lacks binary_media_types, causing
webhook signature verification to silently fail in production. Only one SSM slot
exists for the webhook secret, blocking zero-downtime rotation.

SOLUTION: Extend infra/careervp/api_construct.py with the 4 S-006 constructs.
No new DynamoDB tables.

THINK:
1. Read src/frontend/tests/unit/cdk-infra.test.ts and ssm-cold-start.test.ts —
   these define exact resource names, environment variables, and SSM param paths
   the CDK stack must produce. Use them as the acceptance spec.
2. Read infra/careervp/api_construct.py — find _build_api_gw() and existing Lambda
   patterns to match naming conventions and import style.
3. Read infra/careervp/api_db_construct.py — confirm self.api_db.db (users table)
   and self.api_db.idempotency_db attributes.
4. Read infra/careervp/constants.py — confirm BILLING_LAMBDA, BILLING_RECONCILE_LAMBDA,
   BILLING_WEBHOOK_DLQ, WEBHOOK_SECRET_SSM_PARAM, WEBHOOK_SECRET_PREVIOUS_SSM_PARAM,
   WEBHOOK_SECRET_ENV_VAR, WEBHOOK_SECRET_PREVIOUS_ENV_VAR are present.
5. Identify the correct place to insert billing constructs (after existing Lambdas,
   before NagSuppressions).

THEN:
1. In _build_api_gw(): add binary_media_types=["application/json", "*/*"] to RestApi.
2. Add billing_webhook_dlq SQS Queue using constants.BILLING_WEBHOOK_DLQ,
   retention_period=Duration.days(14), encryption=KMS_MANAGED.
3. Add billing_lambda (handler: careervp.handlers.billing_handler.handler) with env:
   TABLE_NAME, IDEMPOTENCY_TABLE_NAME, constants.WEBHOOK_SECRET_ENV_VAR (via
   ssm.StringParameter.value_for_string_parameter using constants.WEBHOOK_SECRET_SSM_PARAM),
   constants.WEBHOOK_SECRET_PREVIOUS_ENV_VAR (via constants.WEBHOOK_SECRET_PREVIOUS_SSM_PARAM),
   PRICE_ID_MONTHLY, PRICE_ID_QUARTERLY, PAYMENT_PROVIDER="placeholder".
   timeout=30s, memory=256. Grant read-write on both tables.
4. Add billing_reconcile_lambda (handler: careervp.handlers.billing_reconcile_handler.handler)
   with env: TABLE_NAME, PAYMENT_PROVIDER="placeholder". timeout=5min, memory=256.
   Grant read-write on users table only (no idempotency access needed).
5. Add EventBridge Rule with Schedule.cron(hour="2", minute="0") targeting
   billing_reconcile_lambda. Pass {"detail": {"action": "reconcile_subscriptions"}}.
6. Add cw.Alarm on billing_lambda.metric_errors(period=5min, statistic="Sum"),
   threshold=1, evaluation_periods=1, treat_missing_data=NOT_BREACHING.
7. Wire billing routes into API Gateway: POST /billing/checkout, GET /users/me/subscription,
   POST /billing/portal (all JWT-authorised), POST /billing/webhook (no authorizer).

CONSTRAINTS:
- DO use ssm.StringParameter.value_for_string_parameter() for all SSM values.
- DO use self.naming.lambda_name() and self.naming.dlq_name() for all names.
- MUST NOT add any new dynamodb.Table construct.
- DO use constants.* for all string literals (Lambda names, SSM paths, env var keys).

PROHIBITED:
- Hardcoded SSM paths or Lambda names.
- binary_media_types on a route — it belongs on RestApi only.
- New DynamoDB tables of any kind.
- Omitting the EventBridge target — reconciliation must have a real trigger.

OUTPUT:
- MODIFY: infra/careervp/api_construct.py

VERIFY:
# CDK synthesises cleanly with no new DynamoDB tables
cd infra && cdk synth 2>&1 | grep -E "(BillingLambda|BillingReconcile|BillingWebhookDlq|binary_media_types|EventRule|Error)"
# TypeScript unit tests (see TEST_EXECUTION_GUIDE.md §TypeScript Happy-Path Tests)
cd src/frontend && npm run test:unit -- --testPathPattern="cdk-infra|ssm-cold-start"
```

---

## Prompt 2 of 5 — SubscriptionRepository: Verify & Extend (S-002.2, S-004, S-006.3)

**Tests targeted:**
- `src/backend/tests/unit/test_subscription_repository.py`

**Pre-check (status: already completed on `front/cdk-billing`):**
```bash
cd src/backend && uv run pytest tests/unit/test_subscription_repository.py -v --tb=short 2>&1 | tail -30
# Expected on a fresh branch (before implementation): 7 failures
#   — 5 x AttributeError (scan_active_subscriptions missing)
#   — 2 x AssertionError (stale "pk" assertions in TestRecordPaymentEvent)
# Expected after implementation: 35 passed
#
# Note: on front/cdk-billing this prompt is already implemented — pre-check shows 35 passed.
# The same command serves as VERIFY: tests import from the real module, so they validate
# correctness (not just file existence). Deleting scan_active_subscriptions breaks 5 tests.
```

---

```text
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#data-model--single-table-design
@spec docs/frontend/subscription/TEST_EXECUTION_GUIDE.md#python-backend-tests
@pattern src/backend/careervp/dal/subscription_repository.py

ROLE: Python backend engineer auditing and extending a DynamoDB DAL against a strict
single-table schema.

PROBLEM: Two test assertions in TestRecordPaymentEvent use stale "pk" key names and
"attribute_not_exists(pk)" — contradicting the idempotency table schema (PK="id", no sort key).
These cause 2 pre-check failures even though the implementation is already correct.
Additionally, scan_active_subscriptions() required by ReconciliationService does not yet exist.

SOLUTION: Fix the two stale test assertions to match the correct "id" schema, then add
scan_active_subscriptions() with pagination to the implementation.

THINK:
1. Read infra/careervp/api_db_construct.py — find _build_idempotency_table() and confirm:
   partition_key name="id", NO sort_key, time_to_live_attribute="expiration".
2. Read src/backend/careervp/dal/subscription_repository.py — confirm all 4 idempotency
   methods (record_payment_event, delete_payment_event, create_checkout_intent,
   release_checkout_intent) already use "id" as the key attribute correctly.
3. Read src/backend/tests/unit/test_subscription_repository.py — find the two failing
   assertions in TestRecordPaymentEvent: test_uses_attribute_not_exists_condition and
   test_stores_pk_with_payment_event_prefix. These assert "pk" and "attribute_not_exists(pk)"
   which are stale; the correct values are "id" and "attribute_not_exists(id)".
4. Check if scan_active_subscriptions() exists in the repository.

THEN:
1. In test_subscription_repository.py, fix TestRecordPaymentEvent:
   - test_uses_attribute_not_exists_condition: change assertion to
     kwargs['ConditionExpression'] == 'attribute_not_exists(id)'.
   - test_stores_pk_with_payment_event_prefix: change assertion to
     item['id'] == 'PAYMENT_EVENT#{event_id}#{event_type}' (full composite key).
2. Add scan_active_subscriptions(self) -> list[dict[str, Any]] to subscription_repository.py:
   Paginated scan on self._table (users table) with
   FilterExpression=Attr("sk").eq("SUBSCRIPTION#CURRENT") & Attr("#s").eq("active"),
   ExpressionAttributeNames={"#s": "status"}.
   Loop on LastEvaluatedKey until exhausted. Return accumulated items list.

CONSTRAINTS:
- MUST scan self._table (users table), NOT self._idempotency_table.
- DO use ExpressionAttributeNames for reserved words (status, plan, name) in all
  update_item and scan calls.
- MUST paginate — a single scan page is capped at 1 MB.

PROHIBITED:
- Modifying the implementation's key attribute names — they are already correct ("id").
- "pk" or "sk" as key attribute names on any idempotency_table call.
- attribute_not_exists(pk) — must be attribute_not_exists(id).
- Calling scan_active_subscriptions from any HTTP handler.
- Adding a new DynamoDB table or index.

OUTPUT:
- MODIFY: src/backend/tests/unit/test_subscription_repository.py (fix 2 stale assertions)
- MODIFY: src/backend/careervp/dal/subscription_repository.py (add scan_active_subscriptions)

VERIFY:
# Python backend (see TEST_EXECUTION_GUIDE.md §Python Backend Tests)
cd src/backend && uv run pytest tests/unit/test_subscription_repository.py -v --tb=short
# Expected: 35 passed
```

---

## Prompt 3 of 5 — BillingService + billing_handler (S-002, S-003, S-005)

**Tests targeted:**
- `src/backend/tests/unit/test_billing_service.py`
- `src/frontend/tests/unit/checkout.test.ts`
- `src/frontend/tests/unit/subscription-status.test.ts`
- `src/frontend/tests/unit/portal.test.ts`
- `src/frontend/tests/unit/cors.test.ts`
- `src/frontend/tests/integration/concurrent-checkout.integration.test.ts`
- `src/frontend/tests/integration/partial-failure-customer-created.integration.test.ts`
- `src/frontend/tests/integration/stripe-timeout.integration.test.ts`
- `src/frontend/tests/integration/stripe-error-503-customer.integration.test.ts`
- `src/frontend/tests/integration/stripe-error-503-session.integration.test.ts`
- `src/frontend/tests/integration/stripe-rate-limit-429.integration.test.ts`

**Pre-check:**
```bash
# Gate: billing implementation must not exist yet (both files should be missing)
ls src/backend/careervp/logic/billing_service.py \
   src/backend/careervp/handlers/billing_handler.py 2>&1
# Expected: "No such file or directory" for each — implementation not yet created.
# If either file already exists, run VERIFY instead of this prompt.
```

> **Pre-check note:** `test_billing_service.py` defines `BillingService` inline and is
> self-contained — it always passes regardless of whether the real module exists.
> The gate above checks file existence: it fails (files missing) before this prompt
> and passes (files present) after implementation.

---

```
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#group-2-checkout-flow-s-002
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#group-3-subscription-lifecycle-s-003
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#group-5-portal--access-control-s-005
@spec docs/frontend/subscription/TEST_EXECUTION_GUIDE.md#python-backend-tests
@pattern src/backend/careervp/logic/*.py
@pattern src/backend/careervp/handlers/*.py
@pattern src/backend/careervp/payment_providers/interface.py

ROLE: Python backend engineer implementing billing business logic with a payment
provider abstraction layer and Powertools observability.

PROBLEM: BillingService and billing_handler.py do not exist. The checkout flow
needs an atomic lock-then-release pattern (create_checkout_intent / release_checkout_intent)
to prevent duplicate customer creation under concurrent requests.

SOLUTION: Create BillingService with handle_checkout, handle_get_subscription,
handle_portal; create billing_handler.py Lambda entry point.

THINK:
1. Read src/backend/tests/unit/test_billing_service.py in full — this is the primary
   acceptance spec. Note every test case, mock setup, and assertion before writing
   any implementation. The method signatures and return shapes must match exactly.
2. Read src/frontend/tests/unit/checkout.test.ts and subscription-status.test.ts —
   these define the HTTP request/response shapes the handler must produce.
3. Read src/backend/careervp/payment_providers/interface.py — note exact DTOs:
   CustomerRecord.customer_id, CheckoutSession.checkout_url, PortalSession.portal_url.
4. Read src/backend/careervp/dal/subscription_repository.py — note all public methods
   including create_checkout_intent, release_checkout_intent, get_customer_id,
   update_customer_id, get_subscription, upsert_subscription.
5. Read src/backend/careervp/dal/user_repository.py — confirm get_user() return type
   and whether it has an .email attribute or dict key.
6. Read an existing handler (e.g. cv_handler.py or job_handler.py) — copy Powertools
   decorator pattern (logger, tracer, metrics) and response builder usage.
7. Plan handle_checkout state machine:
   a. validate plan in ('monthly', 'quarterly') → 400
   b. check existing active subscription → 409
   c. get existing customer_id
   d. if no customer_id: create_checkout_intent (raises ClientError on conflict → 409),
      then in try/finally: create_customer, update_customer_id; finally: release_checkout_intent
   e. get_price_map, create_checkout_session → return checkout_url

THEN:
1. Create src/backend/careervp/logic/billing_service.py:
   - __init__(self, subscription_repo, user_repo, payment_provider).
   - handle_checkout(user_id, plan, success_url, cancel_url) -> dict:
     Full lock lifecycle. Lock is acquired ONLY when customer_id is absent.
     finally block ALWAYS calls release_checkout_intent.
   - handle_get_subscription(user_id) -> dict:
     Returns {"subscription": <item or None>, "has_active_subscription": bool}.
   - handle_portal(user_id, return_url) -> dict:
     Returns 404 {"error": "no_billing_account"} when customer_id absent.
   - Translate botocore.exceptions.ClientError with ConditionalCheckFailedException
     to 409 {"error": "checkout_in_progress"}.
   - Translate PaymentProviderError to 502/503.

2. Create src/backend/careervp/handlers/billing_handler.py:
   - Cold-start factory _get_billing_service() returning BillingService(
       subscription_repo=SubscriptionRepository(),
       user_repo=UserRepository(),
       payment_provider=PlaceholderPaymentProvider()
     ).
   - Powertools logger/tracer/metrics decorators on the handler function.
   - Route dispatch: POST /billing/checkout, GET /users/me/subscription, POST /billing/portal.
   - _extract_raw_body(event: dict) -> bytes utility (needed in Prompt 4):
     if event.get("isBase64Encoded"): return base64.b64decode(event["body"])
     return (event.get("body") or "").encode("utf-8")
   - CORS headers on all billing route responses (not webhook).

3. Run tests and fix all failures.

CONSTRAINTS:
- DO mock PaymentProviderInterface (not Stripe) in all tests.
- DO wrap create_customer + update_customer_id in try/finally that calls release_checkout_intent.
- MUST check for active subscription BEFORE calling create_checkout_intent.
- DO guard get_user() result against None (user may not have email populated yet).

PROHIBITED:
- import stripe (or any payment SDK) anywhere in logic/ or handlers/.
- Omitting finally: release_checkout_intent — TTL is last-resort, not primary cleanup.
- Acquiring the checkout lock before checking whether an active subscription exists.
- Returning raw DynamoDB items with Decimal types — convert before serialising.

OUTPUT:
- CREATE: src/backend/careervp/logic/billing_service.py
- CREATE: src/backend/careervp/handlers/billing_handler.py

VERIFY:
# Python backend (see TEST_EXECUTION_GUIDE.md §Python Backend Tests)
cd src/backend && uv run pytest tests/unit/test_billing_service.py -v --tb=short
# TypeScript unit (see TEST_EXECUTION_GUIDE.md §TypeScript Happy-Path Tests)
cd src/frontend && npm run test:unit -- --testPathPattern="checkout|subscription-status|portal|cors"
# TypeScript integration (see TEST_EXECUTION_GUIDE.md §TypeScript Critical Hardening Tests)
cd src/frontend && npm run test:integration -- --testPathPattern="concurrent-checkout|partial-failure-customer|stripe-timeout|stripe-error-503|stripe-rate-limit"
```

---

## Prompt 4 of 5 — WebhookService + webhook_handler (S-004)

**Tests targeted:**
- `src/backend/tests/unit/test_webhook_service.py`
- `src/frontend/tests/unit/webhook-checkout.test.ts`
- `src/frontend/tests/unit/webhook-invoice.test.ts`
- `src/frontend/tests/unit/webhook-signature.test.ts`
- `src/frontend/tests/unit/webhook-subscription-updated.test.ts`
- `src/frontend/tests/unit/webhook-subscription-deleted.test.ts`
- `src/frontend/tests/unit/webhook-out-of-order.test.ts`
- `src/frontend/tests/unit/webhook-stale-data-out-of-order.test.ts`
- `src/frontend/tests/integration/webhook-rawbody.integration.test.ts`
- `src/frontend/tests/integration/stripe-idempotency.integration.test.ts`
- `src/frontend/tests/integration/partial-failure-rollback.integration.test.ts`
- `src/frontend/tests/integration/partial-failure-usage-fails.integration.test.ts`

**Pre-check:**
```bash
# Gate: webhook implementation must not exist yet
ls src/backend/careervp/logic/webhook_service.py 2>&1
# Expected: "No such file or directory" — implementation not yet created.
# If file already exists, run VERIFY instead of this prompt.
```

> **Pre-check note:** `test_webhook_service.py` defines `WebhookService` inline and is
> self-contained — it always passes regardless of whether the real module exists.
> The gate above checks file existence: it fails (file missing) before this prompt
> and passes (file present) after implementation.

---

```
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#group-4-webhooks--billing-events-s-004
@spec docs/frontend/subscription/TEST_EXECUTION_GUIDE.md#python-backend-tests
@pattern src/backend/careervp/logic/*.py
@pattern src/backend/careervp/handlers/billing_handler.py

ROLE: Python backend engineer implementing a webhook event processor with dual-secret
rotation and commit-after-work idempotency.

PROBLEM: WebhookService does not exist. The webhook handler is missing raw-body decode,
dual-secret verification, commit-after-work idempotency, stale event guard, and
handlers for all 5 payment event types.

SOLUTION: Create WebhookService; extend billing_handler.py with POST /billing/webhook.

THINK:
1. Read src/backend/tests/unit/test_webhook_service.py in full — this is the primary
   acceptance spec. Note every event type tested, mock setup for _verify_webhook,
   assertions for commit-after-work (delete_payment_event called on exception),
   dual-secret fallback cases, and stale event guard behaviour.
2. Read src/frontend/tests/unit/webhook-*.test.ts files — these define HTTP-level
   request/response shapes the handler must produce (status codes, body format).
3. Understand commit-after-work (the inverse of normal idempotency):
   - Call record_payment_event FIRST (claim slot).
   - Do all DynamoDB work (upsert_subscription + set_unlimited_usage).
   - On ANY exception: call delete_payment_event to release slot, then re-raise (→ 5xx → provider retries).
   - On success: leave the record in place (blocks duplicate delivery).
   This is safe because upsert_subscription is idempotent (put_item).

4. Understand dual-secret verification:
   Try primary_secret first. If PaymentProviderError, try previous_secret (if not None
   and not "none"). If both fail, raise → 400. This allows zero-downtime secret rotation.

5. Understand stale event guard for subscription.updated:
   Read existing record's stripe_event_created (Unix int).
   If incoming event.created <= stored value, discard silently (return 200).

6. Map the 5 event types to their DynamoDB writes (see S-004.1 event routing table).

7. Read billing_handler.py (from Prompt 3) — locate _extract_raw_body and route dispatcher.

THEN:
1. Create src/backend/careervp/logic/webhook_service.py:
   - __init__(self, subscription_repo, payment_provider, primary_secret, previous_secret).
   - _verify_webhook(payload_bytes, sig_header) -> WebhookEvent:
     try primary_secret; on PaymentProviderError try previous_secret if truthy and != "none";
     raise PaymentProviderError if all attempts fail.
   - handle_webhook(payload_bytes, sig_header) -> dict:
     verify → route on event_type → return 200.
     Unknown event types: return {"status": "ignored", "event_type": ...} with 200.
   - _handle_checkout_completed(event): commit-after-work pattern.
     record_payment_event → upsert_subscription + set_unlimited_usage →
     on exception: delete_payment_event + raise.
     Convert all Unix timestamps to ISO 8601 via datetime.utcfromtimestamp().
   - _handle_subscription_updated(event): stale guard then update_item on SUBSCRIPTION#CURRENT.
   - _handle_subscription_deleted(event): update status="canceled", set canceled_at.
   - _handle_invoice_succeeded(event): update payment_failed_count=0, status="active".
   - _handle_invoice_failed(event): increment payment_failed_count, update status="past_due".

2. Extend src/backend/careervp/handlers/billing_handler.py:
   - Add _get_webhook_service() factory:
     Read os.environ["PAYMENT_PROVIDER_WEBHOOK_SECRET_SSM_PARAM"] as primary_secret.
     Read os.environ.get("PAYMENT_PROVIDER_WEBHOOK_SECRET_PREVIOUS_SSM_PARAM", "none")
     as previous_secret.
   - Add POST /billing/webhook route:
     payload_bytes = _extract_raw_body(event)
     sig_header = event["headers"].get("Payment-Provider-Signature", "")
     return webhook_service.handle_webhook(payload_bytes, sig_header)
     On PaymentProviderError from verify: return 400 {"error": "invalid_signature"}.
   - No CORS headers on webhook route (only billing routes need CORS).

3. Run tests and fix all failures.

CONSTRAINTS:
- DO store all provider Unix timestamps as ISO 8601 strings in DynamoDB.
- DO call delete_payment_event in the except block before re-raising.
- MUST use ExpressionAttributeNames for update_item calls touching status, plan, name.
- MUST return 200 for unknown event types — never raise on unrecognised events.

PROHIBITED:
- Calling record_payment_event AFTER the DynamoDB writes (breaks retry safety).
- Raising on unknown event type.
- Hardcoding the webhook secret — read from env at cold-start.
- import stripe anywhere.
- Missing stale event guard on subscription.updated.
- CORS headers on the webhook route.

OUTPUT:
- CREATE: src/backend/careervp/logic/webhook_service.py
- MODIFY: src/backend/careervp/handlers/billing_handler.py (add webhook route + factory)

VERIFY:
# Python backend (see TEST_EXECUTION_GUIDE.md §Python Backend Tests)
cd src/backend && uv run pytest tests/unit/test_webhook_service.py -v --tb=short
# TypeScript unit (see TEST_EXECUTION_GUIDE.md §TypeScript Happy-Path Tests)
cd src/frontend && npm run test:unit -- --testPathPattern="webhook-"
# TypeScript integration (see TEST_EXECUTION_GUIDE.md §TypeScript Critical Hardening Tests)
cd src/frontend && npm run test:integration -- --testPathPattern="webhook-rawbody|stripe-idempotency|partial-failure-rollback|partial-failure-usage"
```

---

## Prompt 5 of 5 — QuotaService + ReconciliationService + Wire-Up (S-001, S-005)

**Tests targeted:**
- `src/backend/tests/unit/test_quota_service.py`
- `src/frontend/tests/unit/trial.test.ts`
- `src/frontend/tests/unit/quota-enforcement.test.ts`
- `src/frontend/tests/unit/backward-compat-missing-subscription.test.ts`
- `src/frontend/tests/unit/backward-compat-missing-usage.test.ts`
- `src/frontend/tests/unit/backward-compat-partial-data.test.ts`
- `src/frontend/tests/unit/lifecycle-trial-no-restart.test.ts`
- `src/frontend/tests/unit/observability-correlation-id.test.ts`
- `src/frontend/tests/unit/observability-metrics.test.ts`
- `src/frontend/tests/integration/state-reconciliation.integration.test.ts`
- `src/frontend/tests/integration/state-divergence-detection.integration.test.ts`
- `src/frontend/tests/integration/lifecycle-resubscribe-after-cancel.integration.test.ts`
- `src/frontend/tests/integration/race-condition-check-create.integration.test.ts`
- `src/frontend/tests/integration/subscription-cache-stale.integration.test.ts`

**Pre-check:**
```bash
# Gate: quota/reconciliation implementations must not exist yet
ls src/backend/careervp/logic/quota_service.py \
   src/backend/careervp/logic/reconciliation_service.py \
   src/backend/careervp/handlers/billing_reconcile_handler.py 2>&1
# Expected: "No such file or directory" for each — implementations not yet created.
# If any file already exists, run VERIFY instead of this prompt.
```

> **Pre-check note:** `test_quota_service.py` defines `QuotaService` inline and is
> self-contained — it always passes regardless of whether the real module exists.
> The gate above checks file existence: it fails (files missing) before this prompt
> and passes (files present) after implementation.

---

```
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#group-1-trial--quota-foundation-s-001
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#group-5-portal--access-control-s-005
@spec docs/frontend/subscription/SUBSCRIPTION_IMPLEMENTATION_SPECS.md#infrastructure-s-006
@spec docs/frontend/subscription/TEST_EXECUTION_GUIDE.md#python-backend-tests
@pattern src/backend/careervp/logic/*.py
@pattern src/backend/careervp/handlers/job_handler.py

ROLE: Python backend engineer wiring quota enforcement into existing job handlers and
implementing nightly subscription reconciliation.

PROBLEM: QuotaService.check_access() is not enforced at POST /jobs or POST /gap-analyses,
meaning any user — including expired trials — can create unlimited applications.
ReconciliationService (nightly subscription sync against payment provider) does not exist.

SOLUTION: Create QuotaService and ReconciliationService; inject check_access() into
job_handler.py and gap_analysis_handler.py; create billing_reconcile_handler.py.

THINK:
1. Read src/backend/tests/unit/test_quota_service.py in full — every test case defines
   the exact check_access() logic, backward compat scenarios, and error codes required.
   Note especially tests for missing subscription row, blocked statuses, trial fallback,
   and the lifecycle-no-restart case.
2. Read src/frontend/tests/unit/backward-compat-*.test.ts and lifecycle-trial-no-restart.test.ts —
   these define the HTTP-level behaviour for edge cases.
3. Read src/backend/careervp/logic/trial_service.py — confirm get_usage(user_id)
   return shape: keys trial_active (bool) and credits_remaining (int).
4. Read src/backend/careervp/handlers/job_handler.py — find the earliest point in the
   POST /jobs handler to inject check_access(), before any DynamoDB writes.
5. Check if gap_analysis_handler.py exists; if so, apply same injection.
6. Plan backward compat for check_access:
   - No SUBSCRIPTION#CURRENT row → fall through to trial check (do not raise).
   - USAGE row absent → treat credits_remaining as 0.
5. Plan reconcile_all(): scan → for each active sub retrieve from provider → compare
   status → upsert on divergence → catch per-user errors to avoid aborting the entire run.

THEN:
1. Create src/backend/careervp/logic/quota_service.py:
   - BLOCKED_STATUSES = frozenset({"past_due", "canceled", "expired"}).
   - __init__(self, subscription_repo, trial_service).
   - check_access(user_id: str) -> None:
     get_subscription(user_id) — if success and status == "active": return.
     if success and status in BLOCKED_STATUSES: raise QuotaError(403, "subscription_required").
     Fall through to trial: get_usage(user_id).
     If not trial_active: raise QuotaError(403, "trial_expired").
     If credits_remaining <= 0: raise QuotaError(403, "trial_exhausted").

2. Create src/backend/careervp/logic/reconciliation_service.py:
   - __init__(self, subscription_repo, payment_provider).
   - reconcile_all(self) -> dict:
     items = subscription_repo.scan_active_subscriptions()
     For each item: try retrieve_subscription(item["subscription_id"]),
       compare provider status to item["status"], call upsert_subscription on divergence.
       On per-user exception: log error, increment errors count, continue.
     Return {"checked": n, "updated": n, "errors": n}.

3. Create src/backend/careervp/handlers/billing_reconcile_handler.py:
   - Guard: if event.get("detail", {}).get("action") != "reconcile_subscriptions":
       return {"status": "ignored"}.
   - Factory _get_reconciliation_service().
   - Powertools logger on handler; log reconcile_complete with result dict.

4. Modify src/backend/careervp/handlers/job_handler.py:
   - Inject QuotaService into the factory.
   - Add quota_service.check_access(user_id) at the top of the POST /jobs handler
     before any DynamoDB writes.
   - Catch QuotaError → return appropriate 403 body from the error table in specs.

5. Modify src/backend/careervp/handlers/gap_analysis_handler.py (if it exists):
   Same injection pattern as job_handler.

6. Run full test suite and fix all failures.

CONSTRAINTS:
- DO NOT raise when SUBSCRIPTION#CURRENT row is absent — silently fall to trial path.
- DO use existing TrialService for trial logic — do not duplicate it in QuotaService.
- MUST catch QuotaError in each handler and return the correct error body and status code.
- DO log each reconciliation divergence at INFO with user_id, old_status, new_status.
- reconcile_all MUST catch per-user exceptions and continue — one bad user must not
  abort the entire nightly run.

PROHIBITED:
- Subscription logic directly in job_handler.py — all logic stays in QuotaService.
- Calling scan_active_subscriptions from any HTTP handler.
- Restarting trial credits after subscription cancellation
  (lifecycle-trial-no-restart.test.ts defines this behaviour).
- Returning 500 from reconcile_all if a single user fails.

OUTPUT:
- CREATE: src/backend/careervp/logic/quota_service.py
- CREATE: src/backend/careervp/logic/reconciliation_service.py
- CREATE: src/backend/careervp/handlers/billing_reconcile_handler.py
- MODIFY: src/backend/careervp/handlers/job_handler.py
- MODIFY: src/backend/careervp/handlers/gap_analysis_handler.py (if exists)

VERIFY:
# Python backend — all subscription tests (see TEST_EXECUTION_GUIDE.md §Python Backend Tests)
cd src/backend && uv run pytest tests/unit/test_quota_service.py \
                                tests/unit/test_billing_service.py \
                                tests/unit/test_webhook_service.py \
                                tests/unit/test_subscription_repository.py -v --tb=short
# TypeScript unit (see TEST_EXECUTION_GUIDE.md §TypeScript Happy-Path Tests)
cd src/frontend && npm run test:unit
# TypeScript integration (see TEST_EXECUTION_GUIDE.md §TypeScript Critical Hardening Tests)
cd src/frontend && npm run test:integration -- --testPathPattern="state-reconciliation|state-divergence|lifecycle-resubscribe|race-condition|subscription-cache"
# Full backend regression (no existing tests broken)
cd src/backend && uv run pytest tests/unit/ -v --tb=short 2>&1 | tail -20
# ── EXIT CRITERION (Prompt 5 = final prompt) ──────────────────────────────────
# ALL tests in src/frontend/tests/ must pass 100% — unit + integration + critical
cd src/frontend && npm run test:unit && npm run test:integration && npm run test:critical
```

---

## Answers to "What Did I Forget?"

After completing all 5 prompts, confirm these cross-cutting items:

| Item | Where to check | Risk if missed |
|------|----------------|----------------|
| `scan_active_subscriptions()` added to `SubscriptionRepository` | Prompt 2 | `ReconciliationService` fails at runtime |
| `get_subscription_by_subscription_id()` may be needed in stale event guard | `test_webhook_service.py` — check if tests call it | Webhook `subscription.updated` handler 500s |
| `UserRepository.get_user()` returns object with `.email` | `user_repository.py` | `BillingService.handle_checkout` NoneType error on customer creation |
| CORS headers on `/billing/checkout`, `/billing/portal`, `/users/me/subscription` — NOT on `/billing/webhook` | `cors.test.ts` | Preflight requests fail in browser |
| Both SSM params exist in account (`previous` set to `"none"` when not rotating) | AWS console / `aws ssm get-parameter` | `cdk synth` or Lambda cold-start fails on first deploy |
| Powertools `@logger.inject_lambda_context` and `@tracer.capture_lambda_handler` on all new handlers | `observability-*.test.ts` | Correlation IDs missing from logs |
| `ExpressionAttributeNames` for `status`, `plan`, `name` in every `update_item` call | Any DynamoDB `update_item` in `webhook_service.py` | `ValidationException: reserved keyword` at runtime |
