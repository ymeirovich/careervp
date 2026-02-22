# Endpoint 2xx Remediation Plan

**Date:** 2026-02-22  
**Goal:** Achieve 2xx responses for all 27 OpenAPI v1 endpoints in strict happy-path tests.

## 1. Baseline

From `docs/refactor/live_tests/test_results_latest.log` (run on 2026-02-22):

- `GET /health` returns `404`.
- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` return `2xx`.
- Most protected endpoints return `403` (`explicit deny` / `no identity-based policy allows execute-api:Invoke`).
- Strict contract test (`test_10_api_contract_success.py`) fails fast at endpoint #1.

## 2. Root Causes

1. API target/env mismatch during testing:
- Test runner prints one default base URL while fixtures use a different default.
- This makes failures difficult to attribute and can hit the wrong deployment.

2. Authz path is failing before business logic:
- Protected routes are denied by API Gateway/authorizer path, so handlers are not consistently reached.

3. OpenAPI route wiring is incorrect in infrastructure:
- In `infra/careervp/api_construct.py`, `_add_openapi_contract_routes()` maps several routes to the wrong lambdas:
  - `/users/me*` mapped to `cv_upload_func` instead of `user_handler`.
  - `/jobs*` mapped to non-job handlers.
  - `/health` mapped to `cv_upload_func` instead of `health_handler`.

4. Handler contract drift vs `docs/refactor2/payloads/*.json`:
- Status code and payload shape mismatches remain (example: some create handlers return `201` where contract expects `200`, and some workflow endpoints still use legacy request shapes).

## 3. Remediation Workstreams

## WS0: Stabilize Target Environment (P0)

### Actions
1. Standardize `API_BASE` source for all live tests:
- Use stack output from CloudFormation as the single source of truth.
- Remove divergent defaults between runner and fixture config.

2. Add preflight check before live tests:
- Verify `/health` and `/auth/login` against the same resolved `API_BASE`.
- Fail early if preflight fails.

### Files
- `docs/refactor/live_tests/run_all_tests.py`
- `docs/refactor/live_tests/conftest.py`

### Exit Criteria
- `run_all_tests.py` and test modules resolve the same base URL.
- Preflight explicitly prints resolved base URL and passes.

## WS1: Fix API Gateway Route→Handler Mapping (P0)

### Actions
1. In `infra/careervp/api_construct.py`, add dedicated lambdas for:
- `user_handler`
- `job_handler`
- `health_handler`

2. Update `_add_openapi_contract_routes()` to map endpoints correctly:
- `/users/me` GET/PUT -> `user_handler`
- `/users/me/cvs` GET -> `user_handler`
- `/users/me/cv` POST -> `cv_upload_handler`
- `/jobs` POST/GET and `/jobs/{jobId}` GET -> `job_handler`
- `/health` GET -> `health_handler`
- Keep existing specialized mappings for VPR, gap-analysis, tailoring, cover-letter, interview-prep, company-research.

3. Keep public route auth settings strict:
- `/auth/*` and `/health` => no authorizer
- all others => custom authorizer

### Files
- `infra/careervp/api_construct.py`
- `infra/tests/infrastructure/test_api_construct.py`

### Exit Criteria
- Synthesized template contains all 27 routes.
- Route integrations point to expected lambda handlers.
- `/health` is deployed and returns 200.

## WS2: Repair AuthN/AuthZ Compatibility (P0)

### Actions
1. Validate JWT key parity for deployed env:
- `/careervp/<env>/jwt-private-key` and `/careervp/<env>/jwt-public-key` must match.
- Tokens minted by `auth_handler` must validate in `api_gateway_authorizer`.

2. Add deploy-time auth canary:
- `POST /auth/login` then `GET /users/me` with returned bearer token.
- Hard fail deployment on non-2xx.

3. During rollout, reduce authorizer cache TTL to prevent stale deny policy behavior.

### Files
- `infra/careervp/api_construct.py` (authorizer cache config)
- `.github/workflows/deploy.yml` (canary step)

### Exit Criteria
- Protected endpoints no longer return authorizer-level 403 for valid access tokens.

## WS3: Align Endpoint Contracts to 2xx Spec (P0/P1)

### Actions by endpoint group
1. Users/CV/Jobs:
- Ensure status/body exactly match refactor2 payload contracts.
- `POST /users/me/cv` should match contract (`201` with `cv_id`, `status`, `parsed_data`).

2. Gap Analysis:
- Normalize response codes and body keys to contract (`questions`, `impact_statements`, etc.).

3. CV Tailoring:
- Support workflow payload (`cv_id`, `job_id`, `vpr_id`, `options`) in generate endpoint.
- Ensure generate returns `202` and status endpoint returns contract-compliant `200`.

4. Company Research:
- `POST /company-research/fetch` should return `202` with request id/status.
- Ensure `GET /company-research/{jobId}` returns contract-compliant completed payload.

5. VPR/Cover Letter/Interview Prep:
- Confirm create endpoints return `202` and status endpoints return `200` with expected structure.
- Persist request IDs and user ownership checks consistently.

### Files
- `src/backend/careervp/handlers/cv_upload_handler.py`
- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/handlers/cv_tailoring_handler.py`
- `src/backend/careervp/handlers/company_research_handler.py`
- `src/backend/careervp/handlers/cover_letter_handler.py`
- `src/backend/careervp/handlers/interview_prep_handler.py`
- `src/backend/careervp/handlers/vpr_submit_handler.py`
- `src/backend/careervp/handlers/vpr_status_handler.py`
- `src/backend/careervp/handlers/user_handler.py`
- `src/backend/careervp/handlers/job_handler.py`
- `src/backend/careervp/handlers/health_handler.py`

### Exit Criteria
- All strict payload assertions pass for status code and body shape.

## WS4: Verification Gates (P0)

### Commands
1. Unit/integration sanity:
```bash
cd src/backend
uv run pytest tests/unit/ -v --tb=short
uv run pytest tests/integration/ -v --tb=short
```

2. Live strict contract:
```bash
cd /Users/yitzchak/Documents/dev/careervp
python docs/refactor/live_tests/run_all_tests.py --test contract --verbose
```

3. Full live suite:
```bash
python docs/refactor/live_tests/run_all_tests.py --verbose
```

### Exit Criteria
- Strict contract module passes all 27 endpoints with `2xx`.
- Full suite has zero module failures.
- Report includes per-endpoint status/body summary.

## 4. Execution Order (Recommended)

1. WS0 (test target unification)  
2. WS1 (route wiring corrections)  
3. WS2 (authorizer/token compatibility)  
4. WS3 (handler contract alignment)  
5. WS4 (gated verification and release)

## 5. Definition of Done

Done means all of the following are true:

1. `test_10_api_contract_success.py` passes all 27 endpoints.
2. Every endpoint returns a `2xx` with valid JSON for happy-path payloads.
3. No 403 authorizer denials for valid tokens on protected routes.
4. `/health` is reachable and returns 200 consistently on deployed API base.
