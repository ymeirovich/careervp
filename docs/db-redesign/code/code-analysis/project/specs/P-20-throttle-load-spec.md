---
spec_id: P-20-THROTTLE-LOAD
title: "Raise API throttle using a minimal load harness"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-20
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; load tests are written later at IMPLEMENT time."
---

# Spec - P-20: API Throttle and Load Harness

## Problem Statement

The dev API stage throttles at 2 rps / burst 10, which can self-DoS normal user flows. The new throttle must be based on a minimal load harness, not guessed, and must remain within the <10k concurrent constraint.

## Evidence

- `infra/careervp/api_construct.py:356-369` creates the RestApi and sets `throttling_rate_limit=2` and burst 10.
- `src/backend/tests/e2e/test_e2e_contract_gate_validation.py:25-37` already names representative generation endpoints for contract probing.
- Scope-lock P-20 requires raising API throttle from 2 rps/burst 10 to a real target and execution-plan step 2.4 requires a locust smoke for hub read plus one generate flow with p99 assertion.

## Fix Plan

1. Add a minimal load harness for health, hub read, and one generate flow with mocked/controlled downstreams where possible.
2. Measure p99, 4xx/5xx, and bootstrap latency under a conservative target.
3. Raise stage throttle to the measured target and document why it is safe for C-1.
4. Preserve CORS and auth behavior; P-30 exact-origin smoke remains the deploy canary.

## RED Tests to Write First

- `test_p20_stage_throttle_not_self_dos`: synth stage settings and assert rate limit is greater than 2 and burst greater than 10.
- `test_p20_load_harness_has_hub_read_and_generate_flow`: inspect load harness config and assert it includes `/applications/{application_id}` or hub read plus one generate endpoint.
- `test_p20_load_harness_asserts_p99_threshold`: run a dry harness config parse; assert a concrete p99 threshold exists and is numeric.
- `test_p20_throttle_change_has_zero_stateful_replacement`: parse `cdk diff` and assert only stage/method settings change.

## Acceptance Criteria

**AC-P20-1** - Given the API stage config, when synthesized, then throttles are above the current 2 rps / burst 10 and tied to load evidence.

**AC-P20-2** - Given the load harness, when it runs in smoke mode, then p99 and error-rate thresholds are evaluated and recorded.

## Done-when

All RED tests pass; load evidence is attached; `cdk diff` zero stateful replacement; naming validator passes.

## Sequencing / Dependencies

May land in Wave 2 after P-30 smoke harness exists. Does not change request/response shapes.

