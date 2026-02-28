# Spec: Cognito-Backed Live API Tests and Non-2xx Remediation

## 1. Purpose
Define a testable, repeatable specification for running live API tests through Cognito-authenticated API Gateway flows, and for eliminating current dominant non-2xx failure patterns.

## 2. Problem Statement
Observed in live runs:
- Excess `401 Unauthorized` on protected routes.
- `403` errors indicating malformed `Authorization` format for routes likely expecting a different authorizer type.
- Contract assertion drift (health payload shape mismatch).
- Error schema assertion mismatch (`error` vs `message`).

This spec requires real-user auth simulation and strict validation gates.

## 3. In Scope
- `docs/refactor/live_tests/conftest.py`
- `docs/refactor/live_tests/test_10_api_contract_success.py`
- `docs/refactor/live_tests/test_11_api_error_contracts.py`
- `docs/refactor/live_tests/README.md`
- Auth/route evidence artifact generation under `docs/beta/evidence/*`

## 4. Out of Scope
- Frontend/UI test flows.
- Production auth model redesign beyond route-authorizer alignment required for these tests.

## 5. Normative Requirements

### R1. Cognito Auth Bootstrap (Real User Flow)
The test harness MUST support creating/ensuring a Cognito user, authenticating, and obtaining JWTs for API calls.

#### R1.1 Required Env Vars
- `COGNITO_REGION`
- `COGNITO_USER_POOL_ID`
- `COGNITO_APP_CLIENT_ID`
- `TEST_EMAIL`
- `TEST_PASSWORD`

#### R1.2 Optional Env Vars
- `COGNITO_APP_CLIENT_SECRET`
- `COGNITO_USE_ADMIN_FLOW` (default `true`)

#### R1.3 Behavior
- Fixture MUST ensure user exists (idempotent).
- Fixture MUST set permanent password when using admin flow.
- Fixture MUST authenticate and return at least one JWT for bearer auth.
- Fixture MUST expose token metadata (token use, expiry, subject).

### R2. Protected-Route Auth Enforcement
Protected tests MUST NOT execute without a valid token unless explicitly negative/auth-failure tests.

#### R2.1 Marker Policy
- Add `@pytest.mark.requires_auth` for protected success tests.
- Missing token in `requires_auth` tests MUST fail fast in CI mode.

### R3. Positive/Negative Suite Separation
- Positive suite validates expected 2xx/contract behavior with valid token.
- Negative suite intentionally validates 401/403/404/422 paths.

### R4. Error Contract Compatibility
Error assertions MUST support gateway/lambda normalized shapes:
- Accept `{"error": ...}` OR `{"message": ...}` depending on source.

### R5. Route Authorizer Consistency
All protected user routes under live test scope MUST use JWT/Cognito-compatible authorizer.
- No protected route may require IAM SigV4 when bearer JWT is the test auth mode.

### R6. Contract Fixture Alignment
Strict contract fixtures MUST match the currently approved API contract.
- Health contract expectations MUST be synchronized (e.g., service keys).

### R7. Documentation and Operator Commands
README MUST include:
- Authenticated run mode
- Negative/error-contract mode
- Required env vars and troubleshooting matrix

## 6. Test Specification

### T1. Auth Bootstrap Tests
File: `docs/refactor/live_tests/test_00_auth_bootstrap.py`
- `test_cognito_login_returns_jwt`
  - Validates token is non-empty JWT-like string.
- `test_users_me_with_real_token_returns_200`
  - Calls `/users/me` with bearer token, expects `200`.

Pass Criteria:
- Both tests pass on staging with configured Cognito env.

### T2. Protected Success Contract Tests
File: `test_10_api_contract_success.py`
- Protected endpoints annotated with `@pytest.mark.requires_auth`.
- All expected-success protected endpoints return 2xx and required schema fields.

Pass Criteria:
- No auth-related 401/403 in positive suite unless explicitly documented exception.

### T3. Error Contract Tests
File: `test_11_api_error_contracts.py`
- Missing token -> expected 401/403 per route policy.
- Invalid/malformed token -> expected 401/403.
- Assertions accept `error` or `message` key (or canonicalized helper output).

Pass Criteria:
- Negative suite passes with intentional non-2xx outcomes only.

### T4. Route Authorizer Audit Test/Script
Artifact: `docs/beta/evidence/I3_auth/route-authorizer-audit.json`
- Enumerates tested routes and authorizer type.
- Flags mismatches (`expected=JWT`, `actual=IAM` etc.).

Pass Criteria:
- Zero mismatches for protected user routes.

### T5. Contract Drift Check
- Validate strict fixtures vs live responses for health and key endpoints.

Pass Criteria:
- Fixture drift is zero or accompanied by approved fixture update in same change.

## 7. Validation Gates (Per Step)

### G1 (After R1)
Run:
- `pytest docs/refactor/live_tests/test_00_auth_bootstrap.py -q`
Gate:
- PASS only if both tests pass.

### G2 (After R2/R3)
Run:
- `pytest docs/refactor/live_tests/test_10_api_contract_success.py -q`
Gate:
- PASS only if protected success paths are 2xx with valid token.

### G3 (After R4)
Run:
- `pytest docs/refactor/live_tests/test_11_api_error_contracts.py -q`
Gate:
- PASS only if expected non-2xx assertions pass with normalized error contract.

### G4 (After R5)
Run:
- route-authorizer audit command/script (implementation-defined)
Gate:
- PASS only if zero protected-route authorizer mismatches.

### G5 (After R6/R7)
Run:
- Full live suite command documented in README
Gate:
- PASS only if summary shows expected success/negative distribution and no unexpected auth drift.

## 8. Evidence Requirements
Upon each gate PASS, update:
- `docs/beta/execution_results/` with gate-specific result markdown
- `docs/beta/evidence/I3_auth/route-authorizer-audit.json` (for G4)
- Any contract drift evidence artifacts

Minimum evidence set for completion:
- Auth bootstrap result log
- Protected success suite result log
- Error contract suite result log
- Route authorizer audit report
- Final consolidated live-test result summary

## 9. Failure Handling Rules
- If token acquisition fails: mark gate FAIL and stop downstream gates.
- If authorizer mismatch detected: mark gate BLOCKED; do not soften assertions.
- If contract drift detected: either update fixture with approval note or revert implementation change; no silent ignores.

## 10. Completion Criteria
This spec is COMPLETE only when:
1. G1-G5 are PASS,
2. Required evidence artifacts are generated and stored,
3. README run instructions are sufficient for operator replay,
4. No unresolved protected-route auth mismatch remains.
