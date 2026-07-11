---
spec_id: D-H7-SCANS
title: "Eliminate request-path DynamoDB Scans"
status: draft
owner: backend
tier: T1
scope_lock_clause: D-H7
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H7: Request-Path Scan Elimination

## Problem Statement

Request-path DynamoDB `Scan` calls do not scale and can leak tenant boundaries. D-H7 eliminates scans from runtime handlers/repositories, retaining scans only in offline migration/admin scripts.

## Evidence

- `src/backend/scripts/cr_migration_backfill.py:261` performs a migration scan, which is acceptable only offline.
- `src/backend/careervp/dal/subscription_repository.py:127-129` still falls back to a money-path scan.
- `src/backend/tests/unit/test_l1_list_endpoints.py:222-272` already contains tests asserting list endpoints use query not scan.
- Scope-lock D-H7 and P-15 both require Scan removal on request paths.

## Fix Plan

1. Inventory `scan(` call sites and classify as request-path, test, or offline migration.
2. Replace request-path scans with keyed `Query`, sparse/high-cardinality GSI, or repository lookup.
3. Add static guard rejecting `scan(` in handler/repository modules except allow-listed offline scripts.
4. Ensure no low-cardinality `STATUS#{status}` GSI partition key is introduced.

## RED Tests to Write First

- `test_dh7_no_scan_in_runtime_handlers_or_dal`: static scan of `src/backend/careervp/{handlers,dal,logic}` asserts no `.scan(` calls outside allow-list.
- `test_dh7_subscription_lookup_uses_query`: patch table; assert subscription lookup uses `query()` and not `scan()`.
- `test_dh7_no_status_only_gsi_partition_key`: synth tables and assert no GSI partition key is `status` or `STATUS#{status}` style low-cardinality.

## Acceptance Criteria

**AC-DH7-1** - Given runtime request paths, when handlers/repositories execute, then DynamoDB Scan is never called.

**AC-DH7-2** - Given new indexes for replacements, when synthesized, then GSI partition keys are user-scoped, high-cardinality, or sparse.

## Done-when

All RED tests pass; P-15 money-path scan test also passes; no frontend contract drift.

## Sequencing / Dependencies

Depends on D-H2 for repository routing. Can share implementation with P-15 where billing paths overlap.

