---
spec_id: D-M-SEAMS-BUNDLE
title: "DAL split, CV dual-key retirement, GSI projection minimization, userEmail PK retirement, access-pattern inventory, DB quick wins"
status: draft
owner: backend
tier: T1
scope_lock_clause: [D-M1, D-M2, D-M3, D-M5, D-M6, D-Q]
tooling:
  D-M1: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-M2: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-M3: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-M5: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-M6: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-Q: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-M* / D-Q: DB Seams Bundle

## Problem Statement

After key authority exists, the DAL seams must be made tractable: split the god-class, stop dual-key CV writes, minimize GSI projections, retire PII `userEmail` partition keys, document access patterns, and apply low-risk DynamoDB quick wins.

## Evidence

- `src/backend/careervp/dal/dynamo_dal_handler.py` is the central DAL file and scope-lock calls it a 1,128-LOC god-class.
- `infra/careervp/api_db_construct.py:337-361` builds a knowledge table with `userEmail` and `knowledgeType`, the PII partition-key target for D-M5/Q-07.
- `infra/careervp/api_db_construct.py:115-117,235-237` creates `user_id-index` GSIs; projection sizes must be audited.
- `src/backend/reports/cr-migration-quarantine-20260617T201543Z.json:521-532` includes CLI smoke user ids from CR migration evidence, showing migration artifacts exist and must be reconciled carefully.
- `src/backend/coverage.xml:2` shows branch coverage is currently zero, making characterization tests important before DAL split.

## Fix Plan

1. D-M1: split DAL by entity/repository behind D-H2 key authority.
2. D-M2: stop dual-key CV writes after migration parity proves legacy and canonical reads match.
3. D-M3: audit all GSIs and minimize projections to required attributes.
4. D-M5: move knowledge/gap PII `userEmail` partition keys to `user_id`/surrogate-based keys.
5. D-M6: write an access-pattern inventory mapping every endpoint/async behavior to Query/GSI, including status-by-artifact and sparse in-flight index.
6. D-Q: add connection reuse, pagination, TTL schema enforcement, and PITR 35-day settings.

## RED Tests to Write First

- `test_dm1_dal_imports_route_to_entity_repositories`: assert handlers import entity repositories rather than the god-class for new paths.
- `test_dm2_cv_write_has_single_canonical_key`: write a CV and assert only canonical key attributes are created after cutover.
- `test_dm2_cv_migration_parity_before_dual_key_retire`: D-H2 harness proves old and new CV reads match.
- `test_dm3_gsi_projections_are_not_all_attributes_unless_justified`: synth tables and fail on `ProjectionType: ALL` without allow-list justification.
- `test_dm5_no_user_email_partition_key`: synth tables and scan repository key builders; assert `userEmail` is not a partition key for knowledge/gap tables.
- `test_dm6_access_pattern_inventory_covers_all_routes`: compare inventory rows with CDK route map and async workers; assert no missing route/worker.
- `test_dq_pagination_pitr_ttl_connection_reuse`: assert list methods paginate, TTL fields are schema-enforced, PITR is 35 days where supported, and clients are module-cached.

## Acceptance Criteria

**AC-DM1-1** - Given new DAL work, when code is inspected, then entity repositories own behavior and the god-class shrinks behind compatibility seams.

**AC-DM2-1** - Given CV writes after cutover, when stored, then exactly one canonical key home is written.

**AC-DM5-1** - Given knowledge/gap storage, when keys are built, then no PII email partition key is used.

**AC-DM6-1** - Given the access-pattern document, when compared to route map and async flows, then every behavior maps to Query/GSI and zero request-path Scans.

## Done-when

All RED tests pass; migration parity evidence exists for D-M2/D-M5; access-pattern inventory is complete; no frontend contract drift.

## Sequencing / Dependencies

Depends on D-H2. D-M6 is a hard dependency of D-H8 later.

