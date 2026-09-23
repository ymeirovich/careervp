---
spec_id: F-CONTRACT-FIXES
title: "Fix four live frontend contract bugs"
status: draft
owner: backend
tier: T1
scope_lock_clause: [F-02, F-03, F-04, F-05]
tooling:
  F-02: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  F-03: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  F-04: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  F-05: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest/vitest files are written later at IMPLEMENT time."
---

# Spec - F-02..F-05: Frontend Contract Fixes

## Problem Statement

The F-01 oracle intentionally fails on four known live mismatches. This spec fixes those backend shapes without breaking the immutable §3 frontend contract or versioning routes.

## Evidence

- `src/frontend/lib/types.ts:70` includes `cancelled` and `expired` in `ArtifactStatus`.
- `src/frontend/lib/types.ts:208-215` expects `VPRStatusResult.download_url`.
- `src/frontend/lib/types.ts:517` requires CV tailoring `vpr_id: string | null` and says null must be present.
- `src/backend/careervp/models/api_models.py:174-179` defines `VPRStatusResult` without `download_url`.
- `src/backend/careervp/models/api_models.py:182` narrows VPR status to `pending|processing|completed|failed`.
- `src/backend/careervp/models/api_models.py:282` requires `CVTailoringRequest.vpr_id: str = Field(min_length=1)`.
- `src/backend/careervp/models/api_models.py:508-521` defines nested `ErrorResponse{error: ErrorObject}`, not the flat frontend envelope.

## Fix Plan

1. F-02: add optional `download_url` to backend VPR status result and populate it where presigned URL is available.
2. F-03: expand backend status literals/models to include `cancelled` and `expired` without removing existing values.
3. F-04: make `vpr_id` present-but-null valid for CV tailoring, and keep omitted distinguishable from null.
4. F-05: expose flat error envelope `{error|message, classification, error_code, field}` on API responses while preserving any internal nested error object only behind internal boundaries.
5. Run F-01/F-06 oracle; these four assertions must flip from RED to GREEN with no test weakening.

## RED Tests to Write First

- `test_f02_vpr_status_result_includes_download_url`: instantiate backend VPR status success fixture and assert `result.download_url` is present when S3 result exists.
- `test_f03_status_literal_accepts_cancelled_and_expired`: validate backend status models with `cancelled` and `expired`; assert no validation error.
- `test_f04_cv_tailoring_vpr_id_accepts_present_null`: validate request with `{'vpr_id': None}`; assert accepted and `model_fields_set` contains `vpr_id`.
- `test_f04_cv_tailoring_vpr_id_omitted_is_distinct`: validate omitted fixture; assert application logic can distinguish omitted from null.
- `test_f05_error_envelope_flat`: API error fixture asserts top-level keys include one of `error`/`message`, plus `classification`, `error_code`, and `field`; nested `error.code` object fails.
- `oracle_known_violations_flip_green`: F-01 oracle failures for F-02..F-05 become green without editing oracle assertions.

## Acceptance Criteria

**AC-F02-1** - Given a completed VPR with a presigned result, when status is returned, then `download_url` is present and frontend-consumable.

**AC-F03-1** - Given status values `cancelled` or `expired`, when backend models validate/emit them, then validation succeeds.

**AC-F04-1** - Given CV tailoring sends `vpr_id: null`, when backend validates the request, then null is accepted and omitted remains distinguishable.

**AC-F05-1** - Given any API error, when parsed by frontend error handling, then the flat envelope fields are available and no `[object Object]` stringification occurs.

## Done-when

All RED tests pass; F-01/F-06 oracle is green for these four; no route versioning and no response-shape regression outside the specified fixes.

## Sequencing / Dependencies

Depends on F-01 oracle. Contract-touching; oracle requirements are mandatory.

