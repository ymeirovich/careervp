---
spec_id: D-H4-P-01-CANONICAL-ARTIFACT
title: "Canonical artifact_id storage and upstream resolution for cover letter/interview prep"
status: draft
owner: backend
tier: T1
scope_lock_clause: [D-H4, P-01]
tooling:
  D-H4: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  P-01: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H4/P-01: Canonical Artifact Routing

## Problem Statement

Cover letter and interview prep fail because upstream artifacts have multiple schemas/keys and `vpr_id` routing is ambiguous. D-H4 stores one canonical `artifact_id` and passes resolved upstreams; P-01 is the user-facing defect this closes.

## Evidence

- `project-scope-lock.md:116` defines P-01 as cover-letter/interview-prep failure caused by 3-schema / `vpr_id` routing.
- `src/backend/careervp/handlers/vpr_status_handler.py:181-193,253-255` projects company research provenance into VPR status. This is a citation delta from the former `:184-192,253`: `_extract_vpr_provenance` is `:181-188`, `_apply_vpr_provenance` is `:190-193`, and the stored-payload `setdefault` loop is `:253-255`.
- `src/backend/careervp/handlers/cv_tailoring_handler.py:983-989` extracts path-parameter artifact ids, confirming the fill-in citation and showing wire ids are route-provided opaque keys.
- `src/frontend/lib/types.ts:74` defines hub `artifact_id: string | null`. This is a citation delta from the fill-in's `:75`; `types.ts:517` still requires CV tailoring to send `vpr_id: null` when absent.
- Scope-lock §3 requires `artifact_id` round-trip, hub `artifact_id` resolvable by status endpoint, and `vpr_id` null-vs-absent preservation.
- `src/backend/careervp/dal/application_repository.py:320-390` writes `artifact_statuses.<type>` and `<type>_artifact_id` in two updates, but `:389-390` swallows every step-2 exception. `src/backend/careervp/handlers/application_handler.py:86-95` then projects the missing value as `artifact_id: null`. A 2026-07-27 moto probe seeded a canonical cover-letter artifact, forced the second update to raise, and observed `{'status': 'pending', 'artifact_id': None}` from the real hub projection. This is D-H4's write-authority defect, not an expansion of D-H3.
- `src/backend/careervp/logic/artifact_dependency_resolver.py:167-172` implements the live six-name ladder in this exact order: `artifact_id`, `artifactId`, `vpr_id`, `company_research_id`, `job_id`, `id`. D-H4 collapses it to `artifact_id`; the other five names are removed from this resolver.
- `src/backend/careervp/handlers/cover_letter_handler.py:320-345` reads the client value through `dal.get_vpr(vpr_id)` at `:327` before checking ownership at `:336-339`. Its `ValueError` currently reaches the broad exception mapping at `:799-808` and becomes a generic HTTP 503.
- `src/backend/careervp/handlers/interview_prep_handler.py:686-727` returns `None` on a jobs-table ownership mismatch at `:703-707`; `:789-827` then falls through to `dal.get_vpr(api_request.vpr_id)` at `:799` and raises only after that second lookup. The broad request mapping at `:481-494` also turns the failure into a generic HTTP 503.
- `src/backend/careervp/handlers/interview_prep_submit_handler.py:144` aliases `application_id`, then `job_id`, then `vpr_id`. This site is **in scope for 3.2**: §3 item 1 and Fix Plan item 4 require `application_id == job_id`, so `vpr_id` may never become the application key.
- `src/backend/careervp/models/api_models.py:340-344` accepts present-null `vpr_id` and rejects omission at model validation. The live handler is a delta: `cv_tailoring_handler.py:600-607` invokes that model only after all three keys are already present, so omission bypasses validation. A 2026-07-27 observable-response probe returned the same stubbed HTTP 202 for present-null and omitted payloads. B-3-6 therefore settles TRUE at the handler boundary even though the model-layer citation in the F-04 evidence is stale.

## Fix Plan

1. Characterize current VPR, CV tailoring, cover letter, and interview-prep artifact ids.
2. Store one canonical opaque `artifact_id` per artifact and route status reads through it.
3. Resolve upstream VPR/CR/CV dependencies through D-H2 repository, not raw client-supplied keys.
4. Keep public `application_id == job_id`, `artifact_id`, and `vpr_id` semantics stable.
5. *(v2.7.0: the "prove migration parity for legacy ids before removing dual-read support" step is removed — all stored data is disposable test data, so there are no legacy ids to carry across. Canonical ids only; see scope-lock O-3.)*

### Pinned 3.2 implementation file list

The four RED tests may drive implementation changes only in:

- `src/backend/careervp/dal/core_repository.py`
- `src/backend/careervp/dal/table_registry.py`
- `src/backend/careervp/dal/application_repository.py` — included because B-3-7 settled FALSE
- `src/backend/careervp/logic/artifact_dependency_resolver.py`
- `src/backend/careervp/handlers/application_handler.py`
- `src/backend/careervp/handlers/cover_letter_handler.py`
- `src/backend/careervp/handlers/interview_prep_handler.py`
- `src/backend/careervp/handlers/interview_prep_submit_handler.py` — the §3 item-1 site is in scope
- `src/backend/careervp/handlers/cv_tailoring_handler.py` — included because B-3-6 settled TRUE at the handler boundary

`src/backend/careervp/models/api_models.py` is not on the list: its present-null and omitted semantics already match AC-DH4-2. The live remaining failure is the handler bypass. That surface overlaps Wave-4 F-04 and is flagged for human review; 3.2 must not mark F-04 closed.

## RED Tests to Write First

- `test_dh4_status_endpoint_resolves_hub_artifact_id`: seed user `user-a`, application/job `job-001`, and canonical cover-letter artifact `cl-001`. Assert `GET /applications/job-001` returns HTTP 200 with `artifacts.cover_letter == {'status': 'completed', 'artifact_id': 'cl-001'}`. Force the second `ApplicationRepository.update_artifact_with_id` update to raise `RuntimeError('forced step-2 artifact_id write failure')`; assert the repository returns `Result(success=False, data=None, code=ResultCode.DYNAMODB_ERROR)` and the hub still resolves `cl-001` from the canonical repository instead of emitting a null identity. Assert the generic resolver accepts `{'artifact_id': 'cl-001'}` and returns `None` for candidates containing only each removed name: `artifactId`, `vpr_id`, `company_research_id`, `job_id`, `id`. This test covers AC-DH4-1.
- `test_p01_cover_letter_uses_resolved_vpr_not_client_key`: for client values `vpr-stale-001` and `vpr-user-b-001`, call cover-letter generation as `user-a` for `job-001`. Assert no `dal.get_vpr` call receives either client value; resolution is scoped to authenticated user `user-a` and application `job-001` before any artifact read. Assert both requests return HTTP 403 with exactly `{'error': 'VPR is not available for this application', 'classification': 'access_denied', 'error_code': 'forbidden', 'field': 'vpr_id'}`. This test covers AC-P01-1.
- `test_p01_interview_prep_uses_resolved_vpr_not_client_key`: repeat the two cover-letter stimuli and assert the identical HTTP 403 body. When the jobs-table path finds `vpr-user-b-001` owned by `user-b`, assert the refusal is terminal and `dal.get_vpr` has zero calls. For submit routing with `application_id=None`, `job_id='job-001'`, and `vpr_id='vpr-user-a-001'`, assert dependency resolution receives `application_id='job-001'`; with both application and job ids absent, assert HTTP 400 with `error='application_id/job_id is required'`, `status_code=400`, and `code=ResultCode.MISSING_REQUIRED_FIELD`, and assert dependency resolution is not called. This test covers AC-P01-1 and preserves §3 item 1 without adding a fifth test.
- `test_dh4_cv_tailoring_preserves_vpr_id_null`: at model validation, assert `CVTailoringRequest.model_validate({'cv_id': 'cv-001', 'job_id': 'job-001', 'vpr_id': None}).vpr_id is None`; assert the same payload without `vpr_id` raises one Pydantic error with `loc == ('vpr_id',)` and `type == 'missing'`. At the handler boundary, stub the accepted downstream path to HTTP 202; assert present-null reaches it once and returns 202. Assert omission returns HTTP 400 with `success is False`, `code == ResultCode.VALIDATION_ERROR`, and a message containing `vpr_id` plus `Field required`; assert the downstream stub is not called for the omitted payload. B-3-6 settled TRUE because the omitted payload currently bypasses model validation, so this is a behavior-changing RED test, not a day-one regression guard. This test covers AC-DH4-2.

Out of scope for all four tests: `company_research_store.py::_legacy_table_name` and the inner `_legacy_read_cover_letter_by_scan` query fallback remain owned by 3.5; `dynamo_dal_handler.py` internal key construction remains owned by a later wave; `infra/` and the D-M god-class/GSI work remain owned by 3.4; request-path Scans remain owned by 3.3; auth, trial, and user-pool keying remain owned by Wave-6 D-H8; F-04 closure remains owned by Wave 4 pending human review of the handler overlap. Scope-lock v2.7.0 remains in force: no parity harness, dual-read window, legacy-id probe, migration, backfill, cutover. No compatibility reader is introduced.

## Affected existing tests (inventory)

Added 2026-07-27 after 3.2-GREEN. The original RED brief carried no
affected-existing-test inventory, which is the root defect behind both §0.3
amendment proposals (`RUNBOOK-RULES.md:301-303`). Both reconciliations below were
human-approved before landing; neither pinned RED test was modified.

- `tests/integration/test_downstream_dependency_202.py::test_cv_tailoring_no_vpr_returns_202_not_500`
  sent `{cv_id, job_id}` with `vpr_id` **omitted** and asserted HTTP 202. That payload
  contradicts scope-lock §3 item 3 (`CV-tailoring sends vpr_id: null (never omitted)` —
  null-vs-absent is load-bearing), the committed oracle schema
  `contract/schemas/CVTailoringRequest.json` (`required: [cv_id, job_id, vpr_id]`), and
  `src/frontend/lib/types.ts:517`. It passed only because of the handler bypass B-3-6
  settled TRUE — the defect AC-DH4-2 exists to remove. **Reconciliation: option 1** —
  the fixture now sends `vpr_id: None`. No contract change; the contract already said this.
- `tests/unit/test_async_submit_handlers.py::test_interview_prep_submit_handler_validates_and_queues_with_sqs_queue_url`
  omitted both `application_id` and `job_id`, relying on
  `interview_prep_submit_handler.py`'s `or api_request.vpr_id` application-key fallback.
  AC-P01-1 requires that request to be refused with HTTP 400 before dependency
  resolution. **Reconciliation: option A1** — the public request contract is tightened
  (v3.0.0) and the fixture now sends `application_id`. The rejected alternative was
  branching on Pydantic `model_fields_set`, which would preserve the fallback behind a
  present-versus-absent check and reintroduce compatibility machinery under a new name.
- **The §0.3 proposal inventoried ONE affected test; the real count is eight.** The
  other seven were found only by running the full suite while landing A1. All seven are
  the same class — fixtures that omitted `application_id` and silently relied on the
  `vpr_id` application-key fallback — so they fall inside the same approved
  reconciliation rather than needing their own. Recorded in full here so no reader
  concludes a single fixture moved, and so the incompleteness of the proposal's
  inventory is itself on the record:
  - `tests/unit/test_async_submit_handlers.py::test_interview_prep_submit_handler_marks_failed_with_artifacts_keys_on_sqs_error` (1)
  - `tests/integration/test_interview_prep_roundtrip.py` — five tests fed by the shared
    `_valid_request_body()` helper: `test_submit_returns_202_with_request_id`,
    `test_submit_writes_pending_artifact_with_artifacts_schema`,
    `test_status_readable_immediately_after_submit`,
    `test_request_id_suffix_matches_artifact_id_format`, `test_cross_user_status_returns_404` (5)
  - plus the one the proposal did name (1) and its sibling above = 8 total.
  Each fixture now sends `application_id`. No assertion was weakened: the
  `applicationId` key in that table is derived from `user_id`, not from the request's
  application id, so adding the field disturbs no stored-key assertion.
  `test_interview_prep_submit_handler_returns_structured_validation_errors` needs no
  change: its payload already fails Pydantic parsing on `gap_response_ids`, which is
  raised before the new handler-level identity guard is reached.

## Acceptance Criteria

**AC-DH4-1** - Given a hub `artifact_id`, when status is requested, then the endpoint resolves that opaque id and returns the same artifact identity.

**AC-P01-1** - Given cover-letter or interview-prep generation, when upstream VPR is needed, then the handler uses resolved owned upstreams and not arbitrary client keys.

**AC-DH4-2** - Given CV-tailoring sends `vpr_id: null`, when parsed by backend, then null is accepted and omitted remains distinguishable.

## Done-when

All RED tests pass; F-01 oracle is green for §3 items 1-3; no route versioning required.

## Sequencing / Dependencies

Depends on D-H2/D-H3. Must precede full P-01 closure and Wave 4 frontend contract fixes that rely on stable artifact ids.
