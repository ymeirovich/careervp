# REFACTOR2 Prompt: Generate Strict Payload-Driven API Tests

Use this prompt to generate a complete API live-test series that must pass all endpoints with successful JSON payloads.

## Copy/Paste Prompt

```md
You are a senior API test engineer working in this repo:
`/Users/yitzchak/Documents/dev/careervp`

## Read First (required)
1. `docs/refactor2/REFACTOR2_PLAN.md`
2. `docs/refactor/live_tests/conftest.py`
3. `docs/refactor/live_tests/run_all_tests.py`
4. `docs/refactor/live_tests/test_01_auth_health.py` through `test_09_company_research.py`
5. `docs/refactor2/payloads/*.json` (canonical endpoint contracts)
6. `docs/refactor/payloads/*.json` (legacy validation context and quality gates)

## Objective
Generate a strict series of live API tests that validates **all 27 endpoints** from `docs/refactor2/payloads` with:
- successful status codes (200/201/202 exactly as specified per payload),
- valid JSON response bodies,
- correct ID chaining across workflow steps,
- async polling to completed status where applicable.

This is a hard requirement from REFACTOR2: no permissive "allow 401/404/422" behavior in happy-path tests.

## Non-Negotiable Constraints
1. Every payload file in `docs/refactor2/payloads` must have a corresponding executed test.
2. Expected HTTP code must match `expected_response.status_code` exactly.
3. Every response body must parse as JSON and be logged in full.
4. Do not keep or add fallback logic that treats 4xx/5xx as pass.
5. Do not skip missing/undeployed endpoints in happy-path tests.
6. Replace static Authorization tokens from payload files with runtime auth from register/login.
7. Resolve all path params dynamically using captured IDs:
   - `{jobId}`, `{vprId}`, `{cvTailoringId}`, `{coverLetterId}`, `{interviewPrepId}`
8. For async generate endpoints returning 202, poll status endpoint until `status == "completed"` or fail on timeout.
9. Validate response shape using keys from `expected_response.body`.
10. Preserve and reuse IDs across tests using shared test state (existing `test_data` + persistence helpers).

## Endpoint Coverage Required (27)
- `/health`
- `/auth/register`, `/auth/login`, `/auth/refresh`
- `/users/me` (GET, PUT), `/users/me/cv`, `/users/me/cvs`
- `/jobs` (POST, GET), `/jobs/{jobId}`
- `/company-research/fetch`, `/company-research/{jobId}`
- `/gap-analysis/questions`, `/gap-analysis/responses`, `/gap-analysis/{jobId}/questions`
- `/vpr/generate`, `/vpr/{vprId}`, `/users/me/vprs`
- `/cv-tailoring/generate`, `/cv-tailoring/{cvTailoringId}`, `/users/me/tailored-cvs`
- `/cover-letter/generate`, `/cover-letter/{coverLetterId}`, `/users/me/cover-letters`
- `/interview-prep/generate`, `/interview-prep/{interviewPrepId}`

## Implementation Requirements
- Reuse the current live test harness style in `docs/refactor/live_tests`.
- Keep deterministic execution order with dependency-safe sequencing.
- Add a payload loader for `docs/refactor2/payloads/*.json`.
- Enrich assertions using relevant legacy payload context from `docs/refactor/payloads`:
  - VPR quality checks (`phase1_vpr_generator_test.json`)
  - Gap tags/impact expectations (`phase2_gap_analysis_test.json`)
  - CV tailoring ATS/FVS checks (`phase3_cv_tailoring_test.json`)
  - Cover letter paragraph/FVS checks (`phase4_cover_letter_test.json`)
  - Interview prep STAR/category checks (`phase6_interview_prep_test.json`)
  - Company research required field checks (`phase8_company_research_test.json`)
- Add a common helper that:
  - executes request from payload spec,
  - injects runtime headers/token,
  - substitutes path params from shared IDs,
  - asserts exact status code and JSON parseability,
  - prints full request/response JSON.
- Add async polling helper for:
  - `vpr`,
  - `cv-tailoring`,
  - `cover-letter`,
  - `interview-prep`,
  - `company-research` (if processing status is returned).

## Files To Create/Update
1. `docs/refactor/live_tests/test_10_api_contract_success.py` (or equivalent strict contract test module)
2. `docs/refactor/live_tests/conftest.py` (only if helper additions are needed)
3. `docs/refactor/live_tests/run_all_tests.py` (include new strict module in run order)

## Required Test Behavior
- Happy-path suite must fail fast on first unexpected status or non-JSON response.
- Keep explicit assertions for key output fields (IDs, status, result blocks, list arrays).
- Ensure generated IDs from create/generate endpoints are persisted for downstream status/list tests.
- Verify completion payload quality where available:
  - VPR has non-empty `uvp` + `differentiators` length >= 3
  - CV tailoring has `ats_score >= 8.0` when present
  - Cover letter includes paragraph metadata when present
  - Interview prep returns questions with STAR-format answers when present

## Run and Verify
Run:
`python docs/refactor/live_tests/run_all_tests.py --verbose`

Then provide:
1. concise change summary,
2. endpoint-by-endpoint pass/fail table (27 rows),
3. any blockers still preventing full success.
```
