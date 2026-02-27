# Canonical Routes

Generated from `docs/refactor/payloads/beta_l6_route_surface_test.json` at 2026-02-27T19:46:50.720794+00:00.

## Canonical Route Set (30)

- GET /health
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- GET /users/me
- PUT /users/me
- GET /users/me/usage
- POST /users/me/cv
- GET /users/me/cv
- POST /jobs
- GET /jobs
- GET /jobs/{job_id}
- POST /jobs/{job_id}/gap-questions
- GET /jobs/{job_id}/gap-questions
- POST /jobs/{job_id}/gap-responses
- GET /applications/{application_id}
- POST /vpr/generate
- GET /vpr/{job_id}/status
- GET /vprs
- POST /cv-tailoring/generate
- GET /cv-tailoring/{job_id}/status
- GET /cv-tailorings
- POST /cover-letter/generate
- GET /cover-letter/{job_id}/status
- GET /cover-letters
- POST /interview-prep/generate
- GET /interview-prep/{job_id}/status
- GET /interview-preps
- GET /company-research/{company_name}
- GET /knowledge-base

## Deprecated Routes To Remove

- /api/cv
- /api/vpr
- /api/cover-letter
- /api/interview-prep
- /api/gap-analysis

## Decision Rule

- Keep only canonical routes listed above in CDK route registration.
- Remove deprecated `/api/*` surface and duplicates after canonical parity verification.
