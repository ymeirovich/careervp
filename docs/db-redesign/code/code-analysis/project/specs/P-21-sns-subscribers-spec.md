---
spec_id: P-21-SNS-SUBSCRIBERS
title: "SNS alarms route to a subscribed on-call topic"
status: draft
owner: infra
tier: T1
scope_lock_clause: P-21
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-21: SNS Alarm Subscribers

## Problem Statement

Alarms publish to a monitoring topic, but the scope lock records zero subscribers. Before migration waves, alarms must reach a real on-call destination.

## Evidence

- `infra/careervp/monitoring.py:62-90` builds the monitoring SNS topic and output.
- `infra/careervp/monitoring.py:106-109,153-156` configures alarm defaults to publish through `SnsAlarmActionStrategy`.
- `infra/careervp/company_research_nested_stack.py:95-128` adds Tavily/company research alarms to the notification topic.
- No `add_subscription` or concrete subscription appears in the monitoring evidence; scope-lock P-21 current state is zero subscribers.

## Fix Plan

1. Add an env-specific subscribed alarm endpoint (email/SMS/PagerDuty webhook per human choice) as a human-confirmed deployment parameter.
2. Ensure every alarm action points at the subscribed topic.
3. Add a deployment proof step to confirm subscription status is `Confirmed`.
4. Do not automate human inbox confirmation; document it as a required console/email step.

## RED Tests to Write First

- `test_p21_monitoring_topic_has_subscription`: synth and assert at least one `AWS::SNS::Subscription` for the monitoring topic in dev/stage/prod config or a required parameter gate that fails closed.
- `test_p21_all_alarm_actions_target_monitoring_topic`: synth alarms and assert each alarm has an action to the monitoring topic.
- `test_p21_subscription_confirmation_evidence_required`: run evidence validator and assert a `Confirmed` subscription ARN/status record is present before P-26/P-21 gate closes.

## Acceptance Criteria

**AC-P21-1** - Given any CloudWatch alarm in the app, when it fires, then it publishes to a topic with at least one confirmed subscriber.

**AC-P21-2** - Given subscription confirmation is human-mediated, when evidence is missing, then the deploy gate remains blocked rather than assuming delivery.

## Done-when

All RED tests pass; confirmed subscription evidence exists; `cdk diff` zero stateful replacement; naming validator passes.

## Sequencing / Dependencies

Wave 0 pre-migration gate and P-26 dependency. Serializes with `monitoring.py` edits.

