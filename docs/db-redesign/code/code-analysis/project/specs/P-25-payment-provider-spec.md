---
spec_id: P-25-PAYMENT-PROVIDER
title: "Payment-provider port, MockProvider HMAC, and StripeProvider freeze-line"
status: draft
owner: backend
tier: T1
scope_lock_clause: [P-25, P-25b]
tooling:
  P-25: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5.3-codex, reasoning: high}}
  P-25b: {claude_code: {model: opus, effort: xhigh}, codex: {model: gpt-5.3-codex, reasoning: max}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-25/P-25b: Payment Provider Port and Real Payments

## Problem Statement

Billing must code against a provider port. MockProvider is valid for launch rehearsal only if its webhook verification is cryptographically meaningful, and paid launch requires StripeProvider with real signature verification before the freeze line.

## Evidence

- `src/backend/careervp/payment_providers/interface.py:144` documents provider interface behavior and cold-start cache expectations.
- `infra/careervp/api_construct.py:2546-2593` wires the billing Lambda and webhook secret parameter names.
- `infra/careervp/api_construct.py:2811-2817,2935-2936` declares `/billing/webhook` as a public route that must verify its own signature.
- `src/backend/docs/swagger/openapi.json:44-62,288` documents checkout, portal, webhook, and subscription surfaces, but swagger is non-authoritative; implementation must preserve frontend-observed shapes.
- Scope-lock P-25b requires Mock HMAC rejection plus StripeProvider before paid launch.

## Fix Plan

1. Define/confirm provider port methods: checkout, portal, verify_webhook, fetch subscription/customer, list/replay events.
2. Implement MockProvider with real HMAC verification and replay/timestamp rejection.
3. Refactor billing logic to depend only on the provider port.
4. Add StripeProvider with real signature verification before paid launch.
5. Preserve checkout/portal URL response shapes and webhook error envelope semantics.

## RED Tests to Write First

- `test_p25_billing_service_depends_on_provider_interface_only`: patch a fake provider; assert billing uses port methods and not concrete Stripe/Mock classes.
- `test_p25_mock_webhook_rejects_tampered_signature`: sign payload, mutate body, assert verification fails.
- `test_p25_mock_webhook_rejects_replay_timestamp`: signed old timestamp fails with exact replay error.
- `test_p25_checkout_portal_contract_shape_preserved`: assert checkout/portal responses contain the same URL fields the frontend consumes.
- `test_p25b_stripe_provider_verifies_real_signature` (AC-P25b-1): obtain a generated fixture secret at runtime from the `PAYMENT_PROVIDER_WEBHOOK_SECRET` environment name; for the exact raw payload whose `id` is `evt_p25b_001` and whose `type` is `checkout.session.completed`, build `t=<now>,v1=<non-matching 64-hex>,v1=HMAC-SHA256(secret, "{t}.{raw_payload}"),v0=<ignored 64-hex>` and assert the returned `WebhookEvent.event_id == "evt_p25b_001"` and `event_type == "checkout.session.completed"` (the matching second `v1` is Stripe's signing-secret-rotation behavior). Then assert three separate negatives: the original valid header with a body mutated from `evt_p25b_001` to `evt_p25b_002` raises `PaymentProviderError.code == "WEBHOOK_SIGNATURE_VERIFICATION_FAILED"`; verification with a separately generated wrong secret raises that same exact code; and a valid digest whose signed timestamp is exactly 301 seconds old raises `PaymentProviderError.code == "WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE"`. Perform local HMAC verification only; call no Stripe API method.
- `test_p25b_paid_launch_gate_fails_without_stripe_provider` (AC-P25b-1): guard the `careervp.payment_providers.stripe_provider.StripeProvider` import inside the test by catching `ModuleNotFoundError` into a `None` sentinel, then assert the sentinel is not `None` with the exact failure reason `StripeProvider missing -> paid launch gate fails` so absence fails on the test's own assertion rather than collection. Assert the class structurally satisfies `PaymentProviderInterface` and has callable `create_customer`, `create_checkout_session`, `create_portal_session`, `construct_webhook_event`, `get_price_map`, and `retrieve_subscription`; then run the shared negative-signature assertion helper used by `test_p25b_stripe_provider_verifies_real_signature` and require the exact tampered-body/wrong-secret code `WEBHOOK_SIGNATURE_VERIFICATION_FAILED` and exact 301-second-stale code `WEBHOOK_TIMESTAMP_OUT_OF_TOLERANCE`.

## Acceptance Criteria

**AC-P25-1** - Given billing code, when provider is swapped by config, then logic uses the provider port and preserves frontend checkout/portal contracts.

**AC-P25-2** - Given MockProvider webhook verification, when body/signature/timestamp are tampered, then verification rejects the event.

**AC-P25b-1** - Given paid launch certification, when StripeProvider or signature negative tests are absent, then the gate fails.

## Done-when

All RED tests pass; no real external API calls in tests; P-14/P-15 can code against the port; secrets stay under P-06 rules.

## Sequencing / Dependencies

P-25 precedes P-14/P-15. P-25b is freeze-line before any paid launch.
