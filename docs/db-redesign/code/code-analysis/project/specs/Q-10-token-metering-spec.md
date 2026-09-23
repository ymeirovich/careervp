---
spec_id: Q-10-TOKEN-METERING
title: "Real token metering, cost-per-app metric, and anomaly alarm"
status: draft
owner: backend
tier: T1
scope_lock_clause: Q-10
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - Q-10: Token Metering

## Problem Statement

Margin decisions currently rely on rough `len/4` token estimates. Q-10 instruments real provider token usage, cost-per-app, prompt-cache hit rate, traffic origin, and anomaly alarms before Sonnet routing decisions depend on margin.

## Evidence

- `project-scope-lock.md:180` defines Q-10 and the pricing model: provisional $20-$30/month subscription, $25 midpoint for gate math, trial 3 apps/14 days.
- `src/backend/careervp/logic/utils/llm_client.py` contains LLM routing/client behavior where token usage must be collected.
- `src/backend/careervp/logic/llm_client.py` still contains legacy `len/4` estimation on the non-router path used by Gap, CV Tailoring, Cover Letter, Interview Prep, and AI Assist.
- `src/backend/careervp/dal/application_repository.py` is the durable application record and is the narrowest existing place to roll up chain-wide LLM cost.
- `infra/careervp/api_construct.py:484-494` builds `llm-cache-table`, and scope-lock notes live cache has zero items, so cache-hit assumptions must be measured.
- `Q-gap-analysis-track-spec.md` requires Q-10 before enabling Gap->Sonnet in production.

## Fix Plan

1. Replace `len/4` metering in billing/telemetry paths with provider-reported usage from Anthropic responses on both LLM clients.
2. Emit per-call metrics/log fields for task mode, model id, input tokens, output tokens, prompt-cache lookup/hit, traffic origin, and cost.
3. Roll up chain-wide LLM usage onto the durable application record so cost-per-app means the full application chain, not only VPR.
4. Record a derived `PRICE_PER_APP` constant for margin gating: provisional midpoint subscription `$25.00` divided by `20` paid applications per subscriber per month = `$1.25/app`.
5. Alarm when measured `CostPerApplicationUSD` for product traffic breaches `0.30 * PRICE_PER_APP = $0.375`.

## Pricing Inputs

- Subscription pricing is still undecided inside the approved range: `$20-$30/month`.
- The provisional gate constant uses the midpoint: `$25/month`.
- Paid usage assumption supplied by product: `20 applications/subscriber/month`.
- Trial plan context: `3 applications total over 14 days`.

Derived constants for Q-10:

- `PRICE_PER_APP = 25.00 / 20 = 1.25`
- `COST_PER_APP_ALARM_THRESHOLD = 0.30 * PRICE_PER_APP = 0.375`

`PRICE_PER_APP` here is a margin-gating constant, not a literal customer-facing per-app SKU price.

## RED Tests to Write First

- `test_q10_router_invoke_records_provider_usage_and_prompt_cache_fields`: fake provider response with usage tokens and cache-read tokens; assert exact tokens/fields are returned and metered.
- `test_q10_legacy_client_generate_records_provider_usage_not_len_div_4`: legacy `LLMClient.generate()` returns exact provider tokens/cost metadata and does not synthesize billing tokens from text length.
- `test_q10_application_repository_rolls_up_chain_llm_usage`: application repository accumulates input/output/cost and returns current application totals.
- `test_q10_cost_per_app_metric_rollup`: two LLM calls inside one bound application context produce exact summed `CostPerApplicationUSD`.
- `test_q10_alarm_threshold_uses_derived_price_per_app`: threshold equals `0.30 * 1.25 = 0.375`.
- `test_q10_monitoring_includes_cost_per_application_alarm`: infra synth contains a CloudWatch alarm on the product `CostPerApplicationUSD` metric at the derived threshold.

## Acceptance Criteria

**AC-Q10-1** - Given an LLM call, when it completes, then real input/output token usage and cost are recorded.

**AC-Q10-2** - Given application-level aggregation, when cost-per-app is computed, then it uses measured call costs from every metered stage in the full application chain, not estimates.

**AC-Q10-3** - Given prompt caching is enabled, when the provider reports cache-read tokens, then prompt-cache hit-rate is measurable from emitted metrics.

**AC-Q10-4** - Given product traffic, when full-chain cost-per-app exceeds `$0.375`, then the CloudWatch alarm breaches.

## Done-when

All RED tests pass; metrics/alarm evidence exists; Q-03 production Sonnet gate can consume measured data.

## Sequencing / Dependencies

Wave 0 step 0.75. Must precede production enabling of Q-03 Sonnet and Q-11 cost-bound decisions.
