# Amendment Proposal — tighten interview-prep submit identity contract

> Emitted per scope-lock §0.3 after 3.2-GREEN found test coverage the
> D-H4/P-01 spec brief did not inventory. This proposal awaits human
> validation. It does not edit either `project-scope-lock` twin, the governing
> spec, any existing test, or either public request-contract artifact.

| Field | Value |
|---|---|
| **clause_id** | `D-H4`, `P-01` |
| **tag** | Both clauses are `status: TARGET`; frontend-contract §3 item 1 and scope-lock v2.7.0/O-3 are affected. |
| **what changed** | The pinned RED test requires an explicit-null `application_id`/`job_id` request to return HTTP 400, while the existing public contract deliberately accepts omission of both fields and falls back to `vpr_id`. Removing that fallback tightens the public request contract. |
| **root defect** | The 3.2-SPEC RED brief omitted the affected-existing-test inventory. It has zero references to `test_async_submit_handlers`, so the required reconciliation was not identified before RED landed. |
| **semver level** | **MAJOR** — the recommended change tightens a documented public/frontend request contract and therefore changes a frontend-contract surface, even though current shipped callers are safe. This is not PATCH bookkeeping. |
| **affected contract twins** | `project-scope-lock.md`, `project-scope-lock.yaml` |
| **affected public contract artifacts** | `src/backend/careervp/models/api_models.py:499-508` (`InterviewPrepRequest` optional-field promise); `src/frontend/lib/types.ts:442-447` (`application_id?`, `job_id?`) |
| **affected spec** | `docs/db-redesign/code/code-analysis/project/specs/D-H4-P-01-canonical-artifact-spec.md` — add the omitted existing-test reconciliation after human approval |
| **affected tests** | `src/backend/tests/unit/test_async_submit_handlers.py::test_interview_prep_submit_handler_validates_and_queues_with_sqs_queue_url`; pinned `src/backend/tests/unit/test_dh4_p01_canonical_artifact.py::test_p01_interview_prep_uses_resolved_vpr_not_client_key` |
| **affected runbook** | `docs/db-redesign/code/code-analysis/project/runbooks/wave-3-status.md` row `3.2-GREEN` |
| **requires adversarial review?** | **Yes** — this tightens a public/frontend contract and touches the v2.7.0/O-3 locked canonical-id decision. |

## Plain-English problem

The two tests use different wire shapes: the existing test omits
`application_id` and `job_id`, while the pinned RED test sends both fields as
explicit null. An implementation could branch on that distinction, but doing
so would keep the old `vpr_id` identity fallback behind a present-versus-absent
check. That is exactly the compatibility family scope-lock v2.7.0/O-3 says to
remove.

## Root defect: the RED brief omitted an affected existing test

The governing spec has no affected-existing-test inventory and contains zero
references to `test_async_submit_handlers`. `RUNBOOK-RULES.md:301-303` covers
this case directly: when needed coverage was not anticipated by the spec, it
must be flagged rather than silently folded into implementation.

The pinned RED test is not itself wrong. The missing work is an explicitly
approved reconciliation of a deliberate existing public contract:

- `careervp/models/api_models.py:504-507` documents that clients may omit the
  two context fields and models both as optional.
- `src/frontend/lib/types.ts:442-447` exposes both fields as optional.
- `test_async_submit_handlers.py:82-110` protects the omission behavior by
  requiring HTTP 202 and an artifact write.

## Evidence that tightening is safe for shipped callers

No current shipped generation path omits both identifiers:

- `src/frontend/app/applications/[id]/page.tsx:126` creates the interview-prep
  generation hook with the page's `jobId`.
- `src/frontend/hooks/useGenerateModule.ts:69-73` sends that value as
  `application_id: jobId`.

The older citation `src/frontend/app/dashboard/jobs/[jobId]/page.tsx:354-357`
does not exist in the current tree because that page is now a 104-line
read-only hub. The current application page plus shared hook are the live
equivalent path; repository-wide search finds no second direct
`generateInterviewPrep` caller.

Fresh test evidence captured on 2026-07-27:

```text
tests/unit/test_async_submit_handlers.py::test_interview_prep_submit_handler_validates_and_queues_with_sqs_queue_url PASSED
tests/unit/test_dh4_p01_canonical_artifact.py::test_p01_interview_prep_uses_resolved_vpr_not_client_key FAILED only at:
assert missing_ids_response['statusCode'] == 400
E assert 409 == 400
```

All independent assertions in the pinned RED test now pass: both ownership
refusals are terminal 403 responses with the pinned envelope, raw client VPR
keys are not read, `job_id` is passed to dependency resolution when
`application_id` is null, and the required CoreRepository method exists. The
remaining event-shape distinction is visible in source:

- `test_async_submit_handlers.py:82-110` omits both identity fields.
- `test_dh4_p01_canonical_artifact.py:364-383` emits both fields as explicit
  null and requires HTTP 400 with no dependency resolution.
- `interview_prep_submit_handler.py:144` currently implements omission
  compatibility with
  `api_request.application_id or api_request.job_id or api_request.vpr_id`.

## Recommended decision

Approve the public-contract tightening and canonical identity rule:

1. Require `application_id` or `job_id` on interview-prep submit requests.
2. Remove the `or api_request.vpr_id` application-key fallback.
3. Change backend and frontend request contracts so the tightening is explicit,
   not an implementation-only surprise.
4. Reconcile the existing submit test in a separate visible
   test-and-contract-only commit.
5. Keep the pinned 3.2 RED test unchanged.

This preserves `application_id == job_id`, removes the old-id compatibility
family, and is safe for the shipped frontend because its live generation path
already sends `application_id`.

## Rejected workaround

Do not branch on Pydantic `model_fields_set` to accept omitted identifiers while
rejecting explicit null. The wire shapes genuinely differ, but branching on
that difference would preserve `vpr_id` as an application-key fallback behind
a present-versus-absent distinction. It contradicts the prompt's canonical-id
only rule and silently reintroduces compatibility machinery under a different
name.

## Human approval path

1. Perform the required adversarial review and confirm or reject the MAJOR
   public-contract tightening.
2. If approved, update both scope-lock twins in one human-executed commit with
   a major version bump, §12/change-log row, twin sync, and
   `Scope-Lock-Approved-By:` trailer.
3. In a separate test-and-contract-only commit, update the omitted existing
   test, `InterviewPrepRequest`, and the frontend `InterviewPrepRequest` type;
   add the missed existing-test inventory to the governing spec.
4. Resume the one blocked 3.2-GREEN assertion, remove the fallback, and run the
   full verification matrix.

Until that stamp lands, `interview_prep_submit_handler.py:144` remains
unchanged and 3.2-GREEN may implement only the independent assertions.
