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

- `project-scope-lock.md:180` defines Q-10 and the pricing model: provisional $20-$30/month subscription, $25 midpoint for gate math, trial 3 apps/14 days, paid apps/subscriber/month still needed.
- `src/backend/careervp/logic/utils/llm_client.py` contains LLM routing/client behavior where token usage must be collected.
- `infra/careervp/api_construct.py:484-494` builds `llm-cache-table`, and scope-lock notes live cache has zero items, so cache-hit assumptions must be measured.
- `Q-gap-analysis-track-spec.md` requires Q-10 before enabling Gap->Sonnet in production.

## Fix Plan

1. Replace `len/4` estimates with provider-reported input/output token usage or official tokenizer where provider usage is unavailable.
2. Emit per-call metrics: task mode, model id, input tokens, output tokens, cache hit/miss, traffic origin, cost.
3. Roll up cost-per-application and cost-per-subscriber estimates.
4. Define `PRICE_PER_APP` or equivalent from human-provided paid usage assumptions; do not guess paid apps/month.
5. Alarm when measured cost-per-app breaches `0.30 * PRICE_PER_APP` or when anomaly detection fires.

## RED Tests to Write First

- `test_q10_len_div_4_estimator_not_used_for_billing_metrics`: static scan/assert cost metric path does not use `len(text) / 4`.
- `test_q10_records_provider_usage_tokens`: fake provider response with usage tokens; assert exact tokens emitted.
- `test_q10_cost_per_app_metric_rollup`: two LLM calls in one application produce exact summed cost metric.
- `test_q10_requires_paid_apps_assumption_before_margin_gate`: missing paid apps/subscriber/month causes margin gate status `blocked_human_input`, not guessed.
- `test_q10_anomaly_alarm_threshold_uses_price_per_app`: assert alarm threshold equals `0.30 * PRICE_PER_APP`.

## Acceptance Criteria

**AC-Q10-1** - Given an LLM call, when it completes, then real input/output token usage and cost are recorded.

**AC-Q10-2** - Given application-level aggregation, when cost-per-app is computed, then it uses measured call costs and cache hits, not estimates.

**AC-Q10-3** - Given margin gate inputs are incomplete, when evaluated, then it flags missing paid usage assumptions and does not guess.

## Done-when

All RED tests pass; metrics/alarm evidence exists; Q-03 production Sonnet gate can consume measured data.

## Sequencing / Dependencies

Wave 0 step 0.75. Must precede production enabling of Q-03 Sonnet and Q-11 cost-bound decisions.

