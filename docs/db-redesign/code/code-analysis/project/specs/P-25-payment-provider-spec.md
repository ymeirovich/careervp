---
spec_id: P-25-PAYMENT-PROVIDER
title: "Payment-provider port, MockProvider HMAC, and StripeProvider freeze-line"
status: draft
owner: backend
tier: T1
scope_lock_clause: [P-25, P-25b]
tooling:
  P-25: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5.5, reasoning: high}}
  P-25b: {claude_code: {model: opus, effort: xhigh}, codex: {model: gpt-5.5-pro, reasoning: xhigh}}
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
- `test_p25b_stripe_provider_verifies_real_signature`: use Stripe test secret/payload fixture; assert valid passes and invalid signature fails.
- `test_p25b_paid_launch_gate_fails_without_stripe_provider`: launch gate asserts provider implementation exists and negative signature tests pass.

## Acceptance Criteria

**AC-P25-1** - Given billing code, when provider is swapped by config, then logic uses the provider port and preserves frontend checkout/portal contracts.

**AC-P25-2** - Given MockProvider webhook verification, when body/signature/timestamp are tampered, then verification rejects the event.

**AC-P25b-1** - Given paid launch certification, when StripeProvider or signature negative tests are absent, then the gate fails.

## Done-when

All RED tests pass; no real external API calls in tests; P-14/P-15 can code against the port; secrets stay under P-06 rules.

## Sequencing / Dependencies

P-25 precedes P-14/P-15. P-25b is freeze-line before any paid launch.

