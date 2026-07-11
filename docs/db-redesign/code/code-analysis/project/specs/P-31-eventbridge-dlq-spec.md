---
spec_id: P-31-EVENTBRIDGE-DLQ
title: "EventBridge scheduled targets use dead-letter queues"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-31
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-31: EventBridge Rule Target DLQs

## Problem Statement

Scheduled EventBridge targets for cleanup and billing reconcile must have DLQs, otherwise failed invocations can vanish without replay.

## Evidence

- `infra/careervp/api_construct.py:2176-2181` creates the hourly cleanup EventBridge rule and target without a DLQ.
- `infra/careervp/api_construct.py:2673-2684` creates the billing reconcile schedule target without a DLQ.
- `infra/careervp/api_construct.py:2536-2541` already has a billing webhook DLQ naming pattern.
- Scope-lock P-31 names cleanup 1h and reconcile 02:00 as EventBridge targets needing DLQs.

## Fix Plan

1. Add one DLQ per scheduled EventBridge target or a shared env-scoped schedule DLQ if ownership is explicit.
2. Configure `targets.LambdaFunction(..., dead_letter_queue=...)` for cleanup and billing reconcile.
3. Add DLQ depth alarms to the monitoring topic.
4. Ensure queue names are explicit and kebab-case via NamingUtils.

## RED Tests to Write First

- `test_p31_cleanup_rule_target_has_dlq`: synth EventBridge targets and assert cleanup target has `DeadLetterConfig`.
- `test_p31_billing_reconcile_target_has_dlq`: assert billing reconcile target has `DeadLetterConfig`.
- `test_p31_eventbridge_dlqs_have_depth_alarms`: synth CloudWatch alarms and assert each schedule DLQ has visible-messages alarm.
- `test_p31_dlq_names_follow_naming_convention`: assert queue names start `careervp-` and end `-{env}`.

## Acceptance Criteria

**AC-P31-1** - Given a scheduled EventBridge target invocation failure, when EventBridge retries are exhausted, then the event is sent to a DLQ.

**AC-P31-2** - Given any schedule DLQ depth > 0, when alarms evaluate, then the subscribed P-21 topic is notified.

## Done-when

All RED tests pass; `cdk diff` zero stateful replacement; naming validator passes.

## Sequencing / Dependencies

Wave 2 reliability/money. Depends on P-21 if alarm delivery is required.

