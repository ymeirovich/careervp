---
spec_id: P-32-COST-OBS-EDGE
title: "Budgets slice, cost anomaly, tags, correlation IDs, log retention, alarms, validators"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-32
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-32: Cost/Observability and Edge Hygiene

## Problem Statement

The Wave 0 slice is human console work: AWS Budgets and Cost Anomaly Detection must be documented and evidenced, not automated. The later P-32 remainder adds tags, correlation-ID propagation, log retention/alarms, and API request validators/models.

## Evidence

- `infra/careervp/monitoring.py:62-90` creates the monitoring topic; P-21 makes it subscribed before relying on alarms.
- `infra/careervp/api_construct.py:356-370` configures API edge settings; validators/models belong near this RestApi.
- `infra/careervp/api_construct.py:887,910,972,1022,1179,1234,1290` and many other Lambda log groups use explicit removal policies; retention must be inventoried.
- `src/backend/careervp/handlers/cors_utils.py:17` shows shared response-header utility; correlation id should propagate through shared handler utilities rather than ad hoc per route.
- Scope-lock P-32 splits Wave 0 budgets/anomaly from Wave 5 tags/correlation/log retention/validators.

## Fix Plan

1. Wave 0: document human console steps to create AWS Budget and Cost Anomaly Detection monitor/subscription; record screenshots/ARNs/thresholds as evidence.
2. Add an evidence validator that fails if budget/anomaly proof is missing.
3. Later remainder: app-wide `Tags.of`, request correlation id from API edge through logs/responses, log retention 30-90d, alarm coverage, and API request validators/models.
4. Do not store console-only configuration as fake CDK code unless AWS ownership is moved into IaC by explicit decision.

## RED Tests to Write First

- `test_p32_budget_console_evidence_required`: evidence validator fails without budget name, threshold, subscriber, and timestamp.
- `test_p32_cost_anomaly_evidence_required`: evidence validator fails without anomaly monitor/subscription proof.
- `test_p32_all_resources_have_required_tags`: synth all stacks and assert required tags include env and feature.
- `test_p32_correlation_id_propagates_to_response_and_logs`: handler fixture with `X-Request-Id` asserts same id in logs and response headers.
- `test_p32_log_retention_between_30_and_90_days`: synth log groups and assert retention window.
- `test_p32_api_routes_have_request_validators_for_body_routes`: synth API methods and assert validators/models on body-bearing routes.

## Acceptance Criteria

**AC-P32-1** - Given Wave 0, when 0.56 is checked, then AWS Budgets and Cost Anomaly Detection evidence exists and is human-created.

**AC-P32-2** - Given later observability work, when synthesized, then tags, retention, alarms, validators, and correlation-id propagation are enforced.

## Done-when

Wave 0 budget/anomaly evidence is documented; later RED tests pass when P-32 remainder is implemented. For infra edits, `cdk diff` zero stateful replacement and naming validator compliance are required.

## Sequencing / Dependencies

Budget/anomaly slice is Wave 0 and remains a console task. Remainder is Wave 5.

