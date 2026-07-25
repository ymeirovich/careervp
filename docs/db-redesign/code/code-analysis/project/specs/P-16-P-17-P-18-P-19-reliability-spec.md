---
spec_id: P-16-P-17-P-18-P-19-RELIABILITY
title: "SQS consumer bounds, partial failures, visibility, and Step Functions retry/heartbeat"
status: draft
owner: infra
tier: T1
scope_lock_clause: [P-16, P-17, P-18, P-19]
tooling:
  P-16: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5.4, reasoning: medium}}
  P-17: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5.4, reasoning: medium}}
  P-18: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5.4, reasoning: medium}}
  P-19: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5.4, reasoning: medium}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-16/P-17/P-18/P-19: Async Reliability

## Problem Statement

Async generation and billing workers must survive retries without silent loss or duplicate storms. Every SQS consumer needs concurrency bounds where rate-limited, partial batch failure reporting, visibility timeout at least six times Lambda timeout, and Step Functions retry/heartbeat settings with full jitter.

## Evidence

- `infra/careervp/api_construct.py:1058-1075,1099-1116,1130-1147` defines VPR, cover letter, and interview prep queues with DLQs and visibility timeouts.
- `infra/careervp/api_db_construct.py:454-532` defines CV upload, gap analysis, and company research queues with DLQs and visibility timeouts.
- `infra/careervp/api_construct.py:1330,1375,1617,1689,2380` attaches SQS event sources; partial batch failure config must be verified on each.
- `src/backend/careervp/handlers/company_research_worker_handler.py:415-428` returns `batchItemFailures`, proving the desired handler pattern exists for at least one worker.
- `infra/careervp/artifact_chain_construct.py:144,175,275` sets heartbeat timeouts; `:158,186,227,251,286` adds retries; `JitterStrategy: FULL` is not evident.

## Fix Plan

1. Inventory every SQS event source and worker handler.
2. P-16: set reserved concurrency or event-source `max_concurrency` for rate-limited workers.
3. P-17: configure `report_batch_item_failures=True` and ensure handlers return `{'batchItemFailures': [...]}` for failed records.
4. P-18: assert every queue visibility timeout is at least six times its consuming Lambda timeout.
5. P-19: add explicit `MaxAttempts`, `BackoffRate`, `JitterStrategy: FULL`, and heartbeat on `StartVPR`.
6. Wire DLQ depth alarms for every DLQ without using low-cardinality `STATUS#{status}` GSI patterns.

## RED Tests to Write First

- `test_p16_rate_limited_consumers_have_max_concurrency`: synth event sources and assert configured max concurrency/reserved concurrency for each rate-limited worker.
- `test_p17_all_sqs_event_sources_report_batch_item_failures`: synth Lambda event source mappings and assert `FunctionResponseTypes` includes `ReportBatchItemFailures`.
- `test_p17_worker_handlers_return_batch_item_failures`: call worker handlers with one failing record and assert `batchItemFailures == [{'itemIdentifier': <failed-message-id>}]`.
- `test_p18_visibility_timeout_at_least_6x_lambda_timeout`: synth queues and functions; assert `visibility_timeout_seconds >= 6 * function_timeout_seconds`.
- `test_p19_sfn_retries_use_full_jitter_and_start_vpr_heartbeat`: synth state machine definition; assert retry policy includes exact `JitterStrategy: FULL`, `MaxAttempts`, `BackoffRate`, and `StartVPR` heartbeat.

## Acceptance Criteria

**AC-P16-1** - Given rate-limited workers, when the template synthesizes, then concurrency is explicitly bounded.

**AC-P17-1** - Given any SQS batch with a per-record failure, when the handler returns, then only failed message ids are listed in `batchItemFailures`.

**AC-P18-1** - Given every SQS queue/consumer pair, when timeouts are compared, then visibility timeout is at least 6x Lambda timeout.

**AC-P19-1** - Given the artifact chain state machine, when synthesized, then retry/heartbeat policy is explicit and uses full jitter.

## Done-when

All RED tests pass; DLQ alarms exist; `cdk diff` zero stateful replacement; naming validator passes.

## Sequencing / Dependencies

P-26 and P-21 should precede additive queue/alarm waves if parent template headroom or subscribed alerting is needed.

