---
spec_id: D-H9-COMPANY-RESEARCH-MIGRATION
title: "Complete FE-UI-044 company research canonical-store migration"
status: draft
owner: backend
tier: T1
scope_lock_clause: D-H9
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H9: Complete Company Research Migration

## Problem Statement

The FE-UI-044 CR canonical-store migration is in flight. D-H9 finishes it by verifying backfill of 239 legacy items, proving dual-read parity, and retiring the legacy `users-table` CR read path that contributes to the 3-schema drift behind P-01.

## Evidence

- `src/backend/scripts/cr_migration_backfill.py:51-124,183,487-506` implements CR migration/backfill modes and reporting.
- `src/backend/scripts/cr_migration_backfill.py:354-355` normalizes `USER#` prefixes, showing legacy key cleanup is already part of migration logic.
- `src/backend/reports/cr-migration-quarantine-20260617T201543Z.json` contains CR migration quarantine evidence.
- `src/backend/careervp/handlers/company_research_worker_handler.py:374-393` checks existing company research artifact status and idempotency.
- `src/backend/careervp/handlers/vpr_submit_handler.py:344-372` loads confident CR artifacts and injects CR context into VPR input.

## Fix Plan

1. Re-run/verify the FE-UI-044 backfill report for the 239 legacy items.
2. Use the D-H2 migration-parity harness to compare legacy `users-table` CR reads to canonical artifacts-table reads.
3. Quarantine mismatches with explicit reason and no silent drop.
4. Retire legacy CR read fallback only after parity passes.
5. Preserve CR status/error fields tolerated by the F-01 oracle.

## RED Tests to Write First

- `test_dh9_backfill_report_counts_239_legacy_items`: fixture report asserts expected legacy item count and no unclassified rows.
- `test_dh9_cr_dual_read_parity_matches_public_projection`: seed legacy and canonical CR; assert D-H2 harness exact projection equality.
- `test_dh9_mismatch_goes_to_quarantine_not_drop`: mismatched CR fixture creates quarantine record with reason.
- `test_dh9_legacy_users_table_cr_read_removed_after_parity`: static scan asserts legacy CR read fallback is absent after cutover.

## Acceptance Criteria

**AC-DH9-1** - Given the legacy CR set, when backfill verification runs, then all 239 items are migrated, skipped as already present, or quarantined with reason.

**AC-DH9-2** - Given canonical CR reads, when VPR/gap/downstream consumers request CR, then they use canonical artifacts and not legacy users-table fallback.

## Done-when

All RED tests pass; parity report is attached; legacy CR fallback is removed; no frontend contract drift.

## Sequencing / Dependencies

Depends on D-H2 parity harness. Helps close P-01 drift family before Wave 4 CR-first work.

