---
spec_id: D-H2-D-H3-KEY-AUTHORITY
title: "Single key-authority repository and ValidationException surfacing"
status: draft
owner: backend
tier: T1
scope_lock_clause: [D-H2, D-H3]
tooling:
  D-H2: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  D-H3: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H2/D-H3: Key Authority and ValidationException Surfacing

## Problem Statement

Key construction is scattered across handlers/DAL code and some `ValidationException`s are swallowed as false "not found." D-H2 creates the single key-authority repository and reusable migration-parity harness. D-H3 ensures malformed key/schema access is surfaced, not hidden.

## Evidence

- `src/backend/careervp/dal/dynamo_dal_handler.py:101` keeps legacy aliases for mixed environments, showing multi-schema compatibility is still present.
- `src/backend/careervp/handlers/cv_tailoring_handler.py:345,577,732,803,858,946,1001-1002,1038` repeatedly constructs DAL handlers from table-name precedence, proving no single key authority governs access.
- `src/backend/careervp/handlers/cover_letter_handler.py:56-63,649,1369,1446` uses `ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME` precedence, contradicting the no-env-var-table-precedence invariant.
- `infra/careervp/api_construct.py:484-494` builds an LLM cache table separately, demonstrating separate tables are acceptable when contract says they stay outside core.
- Scope-lock D-H2 requires `TableRegistry`/`CoreRepository` plus a reusable dual-read migration-parity harness; D-H3 requires surfacing swallowed `ValidationException`.

## Fix Plan

1. Add a `TableRegistry`/`CoreRepository` as the sole artifact key builder and repository entry point.
2. Replace scattered PK/SK string construction behind repository methods, beginning with characterization tests.
3. Build a migration-parity harness that reads a legacy item and the candidate core/canonical read and asserts identical public projection.
4. On DynamoDB `ValidationException`, return a typed error/result and log schema/key mismatch, never convert it to a false 404.
5. Preserve frontend §3 identifiers and response shapes; internal PK/SK changes are not API changes.

## RED Tests to Write First

- `test_dh2_all_artifact_keys_built_by_core_repository`: static scan asserts no handler builds `pk`, `sk`, `USER#`, or artifact SK strings outside approved key-authority modules.
- `test_dh2_migration_parity_harness_reports_identical_projection`: seed legacy and canonical records; assert harness returns `passed=True` and exact projection equality.
- `test_dh3_validation_exception_not_returned_as_not_found`: moto/stub DynamoDB raises `ValidationException`; assert repository returns schema error/result, not `None`/404.
- `test_dh2_no_env_table_precedence_in_handlers`: scan handlers and assert `ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME` fallback chains are absent after migration.

## Acceptance Criteria

**AC-DH2-1** - Given any artifact repository operation, when a key is built, then it is built by the single key-authority module.

**AC-DH2-2** - Given a migration slice, when dual-read parity runs, then legacy and canonical public projections match exactly before cutover.

**AC-DH3-1** - Given a DynamoDB schema/key validation failure, when the repository catches it, then the error is surfaced and observable, not reported as not found.

## Done-when

All RED tests pass; migration-parity harness is reusable by D-H4/D-M2/D-M5/D-H9; no frontend contract drift.

## Sequencing / Dependencies

Wave 3 foundation. Must precede D-H4, D-H7, D-M*, D-H9, and P-01.

