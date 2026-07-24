# P-04 / P-05 — Route × Handler Ownership Matrix (1.1-RED evidence)

**Generated:** 2026-07-24 · **Branch:** db-redesign · **Step:** Wave-1 PROMPT 1.1-RED
**Spec:** `docs/db-redesign/code/code-analysis/project/specs/P-04-P-05-auth-idor-spec.md`

This matrix is a **human-readable snapshot**. The authoritative source is the *live* CDK
`route_map` + `public_paths` in `infra/careervp/api_construct.py`, parsed at test time by
`src/backend/tests/security/p04_p05_route_matrix.py`. The ratchet test
`test_p05_route_matrix_has_owner_assertion_for_every_authenticated_route` reads that live source —
it will fail if a new authenticated resource-by-id route is added without a cross-tenant owner-check
probe. Regenerate this file if the route_map changes.

**Counts:** 40 routes total · 6 public · 34 authenticated (19 resource-by-id / 15 self-collection).

## Classification method

- **PUBLIC** — path is in `api_construct.py`'s `public_paths` set (attached with `authorizer=None`).
- **resource-by-id (IDOR surface)** — authenticated route whose path carries a foreign resource id
  (`{jobId}`, `{vprId}`, `{application_id}`, `{cvTailoringId}`, `{coverLetterId}`,
  `{interviewPrepId}`, `{moduleType}`). The caller's own identity is never in the path (it is
  `/users/me`, taken from the JWT). Every one of these is covered by a cross-tenant probe in
  `src/backend/tests/integration/test_p05_cross_tenant_idor.py`.
- **self/collection** — authenticated route with no foreign id in the path; identity comes only from
  the JWT, so the cross-tenant-by-foreign-id attack does not apply. (These still route through the
  same `extract_user_id` resolver, so the P-04 header-fallback fix protects them too.)

## Matrix

| # | Method | Path | Handler | Class | Owner-check coverage |
|---|--------|------|---------|-------|----------------------|
| 1 | GET | /health | health_api_func | PUBLIC | n/a (unauthenticated by design) |
| 2 | GET | /users/me | user_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 3 | PUT | /users/me | user_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 4 | GET | /users/me/usage | user_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 5 | POST | /users/me/trial/reset | user_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 6 | POST | /users/me/cv | cv_upload_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 7 | GET | /users/me/cv | user_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 8 | GET | /users/me/subscription | billing_lambda | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 9 | POST | /jobs | job_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 10 | GET | /jobs | job_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 11 | GET | /jobs/{jobId} | job_api_func | resource-by-id | cross-tenant probe: YES |
| 12 | POST | /jobs/{jobId}/gap-questions | gap_api_func | resource-by-id | cross-tenant probe: YES |
| 13 | GET | /jobs/{jobId}/gap-questions | gap_api_func | resource-by-id | cross-tenant probe: YES |
| 14 | POST | /jobs/{jobId}/gap-responses | gap_api_func | resource-by-id | cross-tenant probe: YES |
| 15 | GET | /applications/{application_id} | application_api_func | resource-by-id | cross-tenant probe: YES |
| 16 | POST | /vpr/generate | vpr_submit_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 17 | GET | /vpr/{vprId}/status | vpr_status_func | resource-by-id | cross-tenant probe: YES |
| 18 | POST | /vpr/{vprId}/cancel | vpr_status_func | resource-by-id | cross-tenant probe: YES |
| 19 | GET | /vprs | vpr_status_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 20 | POST | /cv-tailoring/generate | cv_tailoring_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 21 | GET | /cv-tailoring/{cvTailoringId}/status | cv_tailoring_func | resource-by-id | cross-tenant probe: YES |
| 22 | POST | /cv-tailoring/{cvTailoringId}/cancel | cv_tailoring_func | resource-by-id | cross-tenant probe: YES |
| 23 | DELETE | /cv-tailoring/{cvTailoringId} | cv_tailoring_func | resource-by-id | cross-tenant probe: YES |
| 24 | PATCH | /cv-tailoring/{cvTailoringId} | cv_tailoring_func | resource-by-id | cross-tenant probe: YES |
| 25 | GET | /cv-tailorings | cv_tailoring_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 26 | POST | /cover-letter/generate | cover_letter_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 27 | GET | /cover-letter/{coverLetterId}/status | cover_letter_status_func | resource-by-id | cross-tenant probe: YES |
| 28 | POST | /cover-letter/{coverLetterId}/cancel | cover_letter_status_func | resource-by-id | cross-tenant probe: YES |
| 29 | PATCH | /cover-letter/{coverLetterId} | cover_letter_status_func | resource-by-id | cross-tenant probe: YES |
| 30 | GET | /cover-letters | cover_letter_status_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 31 | POST | /interview-prep/generate | interview_prep_api_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 32 | GET | /interview-prep/{interviewPrepId}/status | interview_prep_status_func | resource-by-id | cross-tenant probe: YES |
| 33 | POST | /interview-prep/{interviewPrepId}/cancel | interview_prep_status_func | resource-by-id | cross-tenant probe: YES |
| 34 | GET | /interview-preps | interview_prep_status_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 35 | GET | /company-research/{jobId} | company_research_func | resource-by-id | cross-tenant probe: YES |
| 36 | POST | /company-research/{jobId}/cancel | company_research_func | resource-by-id | cross-tenant probe: YES |
| 37 | POST | /company-research/fetch | company_research_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 38 | GET | /knowledge-base | company_research_func | self/collection | self-scoped (JWT identity; no foreign id in path) |
| 39 | POST | /billing/webhook | billing_lambda | PUBLIC | n/a (unauthenticated by design) |
| 40 | GET | /jobs/{jobId}/artifacts/{moduleType}/export | export_lambda | resource-by-id | cross-tenant probe: YES |

**Public paths (live):** `/auth/login`, `/auth/refresh`, `/auth/register`, `/billing/webhook`, `/errors`, `/health`
**Handlers covered by a cross-tenant probe (9):** application_api_func, company_research_func, cover_letter_status_func, cv_tailoring_func, export_lambda, gap_api_func, interview_prep_status_func, job_api_func, vpr_status_func

## What the RED tests establish (verified 2026-07-24)

The real, systemic vulnerability is **one shared function**, not per-handler: every authenticated
handler resolves identity through `careervp.handlers.auth_utils.extract_user_id`, which — when a
request arrives without Cognito authorizer claims — falls back to trusting a **client-supplied
`x-user-id` header** (`handlers/auth_utils.py:44`). A forged `x-user-id: <victim>` therefore makes
the caller "become" the victim, defeating each handler's already-present owner check.

- 8 of the 9 covered handlers return **HTTP 200 with the victim's resource** under a forged-header
  cross-tenant request today (jobs and company-research even echo the victim's title in the body).
- **`export_lambda` is the exception and already fails closed (401)**: `export_handler` reads
  `requestContext.authorizer.claims.sub` **directly** and never calls `extract_user_id`, so the
  header fallback does not reach it. Its probe passes today and is a regression guard, not a RED —
  **the GREEN session need change nothing in `export_handler`** (it is the reference for the correct
  identity pattern).
- After P-04 removes the header fallback, `extract_user_id` returns `None` for a claims-less request
  and every covered handler returns **401** — confirmed by simulating the post-fix world (no claims,
  no header) against all 9 handlers.
