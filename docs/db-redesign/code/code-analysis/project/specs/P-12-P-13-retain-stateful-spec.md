---
spec_id: P-12-P-13-RETAIN
title: "RETAIN/deletion protection for stateful resources and dead RETAIN stack cleanup"
status: draft
owner: infra
tier: T1
scope_lock_clause: [P-12, P-13]
tooling:
  P-12: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
  P-13: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - P-12/P-13: Stateful Retention

## Problem Statement

Tables and buckets still use `RemovalPolicy.DESTROY` and some buckets use `auto_delete_objects=True`, which violates the stateful-resource invariant. P-13 removes dead RETAIN stack code that is not instantiated so safety is real, not aspirational.

## Evidence

- `infra/careervp/api_db_construct.py:101,142,164-165,220,267,292,330,356,396,433,547-548,584-585,601-602,636-637,670-671` shows stateful DynamoDB/S3 resources using `RemovalPolicy.DESTROY` and buckets with `auto_delete_objects=True`.
- `infra/careervp/api_construct.py:348,504,887,910,972,1022,1179,1234,1290,1348,1393,1462,1526,1586,1659,1729,1793,1837,1871,1912,1952,2016,2197,2262,2301,2344,2393,2432,2471,2508,2554,2604,2645` shows many log groups/Lambdas using DESTROY; only stateful resources are in scope for P-12.
- `infra/careervp/dynamodb_stack.py:30-94` and `infra/careervp/s3_stack.py:30-63` show retained but separate stack code, which must be checked for instantiation before relying on it.
- Scope-lock P-12 requires `RETAIN` + deletion protection on all tables/buckets and fixing backups bucket auto-delete.

## Fix Plan

1. Inventory every DynamoDB table and S3 bucket in synthesized templates.
2. Set DynamoDB removal policy to RETAIN and deletion protection to true where supported. Ensure PITR expectations are not weakened.
3. Set all user/stateful S3 buckets to RETAIN and `auto_delete_objects=False`.
4. Leave ephemeral log groups/queues out of P-12 unless they are stateful under the contract.
5. P-13: remove or clearly mark dead RETAIN stack modules only if synth proves they are not instantiated.

## RED Tests to Write First

- `test_p12_all_dynamodb_tables_retain_and_deletion_protected`: synth and assert every `AWS::DynamoDB::Table` has `DeletionPolicy: Retain`, `UpdateReplacePolicy: Retain`, and deletion protection enabled.
- `test_p12_all_stateful_buckets_retain_no_auto_delete`: synth and assert every user/artifact/upload/backup bucket has retain policies and no auto-delete custom resource.
- `test_p12_cdk_diff_zero_stateful_replacement`: parse `cdk diff` artifact and assert no Table/Bucket replacement.
- `test_p13_dead_retain_stacks_not_instantiated_or_removed`: assert obsolete retained-stack modules are either not imported/instantiated or removed by this clause.
- `test_p12_naming_validator_passes`: run naming validator and assert zero violations.

## Acceptance Criteria

**AC-P12-1** - Given synthesized stateful resources, when inspected, then all DynamoDB tables and S3 buckets are retained and protected from deletion/replacement.

**AC-P12-2** - Given `cdk diff`, when the RETAIN change is prepared, then it shows zero stateful replacement.

**AC-P13-1** - Given dead RETAIN stack code, when synth/import graph is inspected, then no safety claim depends on an uninstantiated stack.

## Done-when

All RED tests pass; `cdk diff` zero stateful replacement; naming validator passes; P-29 evidence pack and P-30 baseline smoke are complete before deploy.

## Sequencing / Dependencies

Wave 0 deploy #1. Depends on P-27/P-28, P-29, and P-30. Serializes with `api_db_construct.py`/`app.py` edits.

