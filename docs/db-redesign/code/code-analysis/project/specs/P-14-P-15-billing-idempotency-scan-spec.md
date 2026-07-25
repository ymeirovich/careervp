---
spec_id: P-14-P-15-BILLING-IDEMPOTENCY-SCAN
title: "Billing idempotency and money-path Scan removal"
status: draft
owner: backend
tier: T1
scope_lock_clause: [P-14, P-15]
tooling:
  P-14: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5.3-codex, reasoning: high}}
  P-15: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5.3-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-14/P-15: Billing Idempotency and No Money-Path Scan

## Problem Statement

Billing must be launch-safe: webhook and at-least-once worker paths need stable idempotency keys, and money-path subscription/customer lookups must not use DynamoDB `Scan`. This spec depends on the P-25 provider port but can define the exact tests now.

## Evidence

- `infra/careervp/api_db_construct.py:131-142` builds an idempotency table, but scope-lock says it is empty/unwired.
- `infra/careervp/api_db_construct.py:206-230` defines an `idempotency-key-index`, proving duplicate-detection infrastructure exists.
- `infra/careervp/api_construct.py:2562-2573` wires `billing_handler.handler` with idempotency table and webhook-secret parameter env vars.
- `infra/careervp/api_construct.py:2637-2662` wires `billing_reconcile_handler.handler`.
- `infra/careervp/api_construct.py:2671-2681` schedules billing reconciliation through EventBridge.
- `infra/careervp/api_construct.py:661` grants `dynamodb:Scan`, which must not remain on the billing money path.

## Fix Plan

1. After P-25, key webhook idempotency by provider event id and provider name.
2. Key worker idempotency by stable business id (`application_id`, artifact type, operation, provider event id where applicable), never by request timestamp.
3. Replace billing customer/subscription scans with a customer-id or subscription-id GSI/query path.
4. Make duplicate webhook replay return the same recorded result and no duplicate side effects.
5. Keep checkout/portal URL response shapes stable for the frontend.

## RED Tests to Write First

- `test_p14_webhook_replay_same_event_id_single_side_effect` (AC-P14-1): send the same MockProvider-signed `checkout.session.completed` event twice through `WebhookService.handle_webhook` against a moto idempotency table; assert `upsert_subscription` is called exactly once and both deliveries return exactly `{'status_code': 200}` (the second delivery replays that recorded result, with no second side effect).
- `test_p14_worker_replay_same_business_id_single_artifact` (AC-P14-2): invoke the company-research SQS worker twice for `application_id=app-p14-001`, artifact type `company_research`, and operation `generate`; assert the stable key is exactly `WORKER_OPERATION#app-p14-001#company_research#generate` (never timestamp-derived), `_async_process_record` is called exactly once, and the moto idempotency table contains exactly one record with that key.
- `test_p15_billing_lookup_uses_query_not_scan` (AC-P15-1): drive `SubscriptionRepository.get_subscription_by_customer_id('cus_p15_001')`; assert `query()` is called on exactly `customer-id-index` with `Key('customer_id').eq('cus_p15_001')`, and assert `scan()` is never called.
- `test_p15_iam_money_path_has_no_scan_permission` (AC-P15-1): synth the `BillingLambda` construct (physical function `careervp-billing-lambda-dev`, handler `careervp.handlers.billing_handler.handler`) and assert no IAM statement attached to its execution role includes `dynamodb:Scan`; the separate `BillingReconcileLambda` is outside this assertion.
- `test_p14_idempotency_ttl_is_set` (AC-P14-1): assert a payment-event idempotency record carries the `expiration` TTL attribute and that `expiration - claim_epoch` is exactly `604800` seconds (7 days).
- `test_p25_mock_event_id_is_stable_across_retries` (AC-P14-1; bet B-2-2): verify the same logical MockProvider event twice through `construct_webhook_event`, assert both verified deliveries have the same `event_id`, then deliver both through `WebhookService.handle_webhook` against a moto idempotency table and assert exactly one subscription mutation and one payment-event idempotency record.

## Acceptance Criteria

**AC-P14-1** - Given duplicate provider webhook delivery, when the same event id is processed twice, then exactly one billing state transition occurs and both responses are deterministic.

**AC-P14-2** - Given at-least-once worker replay, when the same business id is retried, then duplicate side effects are suppressed.

**AC-P15-1** - Given subscription/customer lookup on the billing path, when repository methods run, then DynamoDB `Query` is used and `Scan` is never called or permitted.

## Done-when

All RED tests pass; P-25 provider port is used; no frontend checkout/portal contract drift; `cdk diff` zero stateful replacement; naming validator passes if infra changes.

## Sequencing / Dependencies

P-25 precedes this spec. P-26 must precede any additive infra if parent stack headroom is needed.
