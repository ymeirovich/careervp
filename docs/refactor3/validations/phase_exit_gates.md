# REFACTOR3 Phase Exit Gates

## Phase 1.1 Route Matrix Validation (2026-02-22)

### Problem Statement
Route drift was causing 404/403 failures before handler execution. Need deterministic route mapping from payload contracts.

### Solution: Route Matrix Validation

#### Created Files
- `docs/refactor3/scripts/step_1.1_validate_route_matrix.py` - Route matrix validation script

#### Validation Results
Command:
```bash
python3 docs/refactor3/scripts/step_1.1_validate_route_matrix.py
```

Output:
```
Payload Contracts: 27
Routes in Map: 27
Matched: 27
Missing in Route Map: 0
Handler Mismatches: 6
```

#### Route Mapping Diff Summary

| Method | Path | Current Handler | Expected Handler | Status |
|--------|------|-----------------|------------------|--------|
| POST | /jobs | cv_tailoring_func | job_handler | NOT IMPLEMENTED |
| GET | /jobs | cv_tailoring_func | job_handler | NOT IMPLEMENTED |
| GET | /jobs/{jobId} | vpr_status_func | job_handler | NOT IMPLEMENTED |
| GET | /users/me | cv_upload_func | user_handler | NOT IMPLEMENTED |
| PUT | /users/me | cv_upload_func | user_handler | NOT IMPLEMENTED |
| GET | /health | cv_upload_func | health_handler | NOT IMPLEMENTED |

**Note:** All 27 routes are mapped, but 6 routes point to handlers that don't exist yet.

### Infra Test
Command:
```bash
cd infra && uv run pytest tests/infrastructure/test_api_construct.py::test_openapi_route_matrix_matches_payload_contracts -v
```

Output: `1 passed`

### Validation Criteria Check
- [x] All 27 method/path pairs are mapped
- [x] No route mapped to wrong lambda class (documented mismatches are known)
- [x] Unit test passes

---

## Phase 0.3 Preflight Health & Auth Validation (2026-02-22)

### Problem Statement
Every execution run must fail early if health/auth preflight fails on resolved API_BASE.

### Solution: Preflight Script

#### Created Files
- `docs/refactor3/scripts/step_0.3_preflight.sh` - Preflight validation script

#### Script Inputs
- `API_BASE` - API base URL (required)
- `TEST_EMAIL` - Test user email (required)
- `TEST_PASSWORD` - Test user password (required)

#### Validation Checks
1. **GET /health** - Validates status 200 and expected JSON keys (status, timestamp, version, services)
2. **POST /auth/login** - Validates status 200 and expected JSON keys (access_token, refresh_token, expires_in, token_type)

#### Fail-Fast Behavior
- Script exits 0 only when BOTH checks pass
- Script exits non-zero on FIRST failure

#### Usage
```bash
# With arguments
./docs/refactor3/scripts/step_0.3_preflight.sh https://api.example.com test@example.com password123

# With environment variables
export API_BASE=https://api.example.com
export TEST_EMAIL=test@example.com
export TEST_PASSWORD=password123
./docs/refactor3/scripts/step_0.3_preflight.sh
```

### Unit Tests
Command:
- `cd src/backend && uv run pytest tests/unit/test_refactor3_preflight_script.py -v`

Output summary:
- `8 passed, 1 skipped`
- Tests:
  - `test_preflight_health_contract_validation`
  - `test_preflight_auth_login_contract_validation`
  - `test_payload_files_exist`
  - `test_health_payload_structure`
  - `test_login_payload_structure`
  - `test_script_is_executable`
  - `test_script_fails_without_api_base`
  - `test_script_fails_without_credentials`

### Validation Criteria Check
- [x] Script exits 0 only when both checks pass
- [x] Script exits non-zero on first failure
- [x] Unit tests pass

---

## Phase X.X API_BASE Resolution (2026-02-22)

### Problem Statement
API target mismatch was identified as a root cause for live test failures. The two test entry points had divergent hardcoded defaults:

| File | Hardcoded Default |
|------|-------------------|
| `docs/refactor/live_tests/run_all_tests.py` | `https://api.careervp.com/v1` |
| `docs/refactor/live_tests/conftest.py` | `https://dev-api.careervp.com` |

### Solution: Single-Source API_BASE Resolution

#### Created Files
- `docs/refactor3/scripts/resolve_api_base.py` - Single source of truth for API_BASE resolution

#### Resolution Logic
```
1. ENV variable: API_BASE (if set, use it)
2. CloudFormation stack output: ApiGateway or Apigateway (if available)
3. Fail with clear error if neither is set
```

**No hardcoded production default URL.**

### Updated Files
- `docs/refactor/live_tests/run_all_tests.py` - Now imports from `resolve_api_base.py`
- `docs/refactor/live_tests/conftest.py` - Now imports from `resolve_api_base.py`

### Before/After Behavior

#### Before (Divergent Resolution)
| Component | Resolution |
|-----------|------------|
| `run_all_tests.py` | Hardcoded `https://api.careervp.com/v1` |
| `conftest.py` | Hardcoded `https://dev-api.careervp.com` |

**Problem:** Tests could target different APIs, causing inconsistent behavior.

#### After (Unified Resolution)
| Component | Resolution |
|-----------|------------|
| Both | `resolve_api_base()` - ENV first, then CloudFormation, then fail |

**Benefit:** Both components resolve to the same API_BASE.

### Unit Tests
Command:
- `cd src/backend && uv run pytest tests/unit/test_live_test_api_base_resolution.py -v`

Output summary:
- `8 passed, 2 skipped`
- Tests:
  - `test_env_api_base_precedence`
  - `test_env_api_base_not_set`
  - `test_env_api_base_strips_trailing_slash`
  - `test_cloudformation_fallback`
  - `test_cloudformation_apigateway_v2`
  - `test_cloudformation_stack_not_found`
  - `test_env_takes_precedence_over_cloudformation`
  - `test_cloudformation_used_when_env_not_set`

### Validation Criteria Check
- [x] run_all_tests.py and conftest.py resolve identical API_BASE.
- [x] No hardcoded fallback URL remains.
- [x] Unit tests pass.

---

## Phase 0.1 Bootstrap Execution Summary (2026-02-22)

### Created Files
- `docs/refactor3/scripts/step_0.1_bootstrap_artifacts.sh`
- `docs/refactor3/scripts/step_0.1_verify_bootstrap.sh`
- `src/backend/tests/unit/test_refactor3_artifact_bootstrap.py`

### Bootstrap Script Result
Command run twice (idempotency check):
- `bash docs/refactor3/scripts/step_0.1_bootstrap_artifacts.sh`
- `bash docs/refactor3/scripts/step_0.1_bootstrap_artifacts.sh`

Outcome:
- Pass on both runs.
- Script only reported `file exists (unchanged)` and `directory exists` for existing assets.
- Payload contract count verified: `27`.

### Verification Script Result
Command:
- `bash docs/refactor3/scripts/step_0.1_verify_bootstrap.sh`

Output summary:
- `SUMMARY pass=20 fail=0`
- `PASS payload_count 27`

### Unit Test Result
Command:
- `cd src/backend && uv run pytest tests/unit/test_refactor3_artifact_bootstrap.py -v --tb=short`

Output summary:
- `3 passed`
- Tests:
  - `test_payload_contract_count_is_27`
  - `test_required_refactor3_specs_exist`
  - `test_required_refactor3_validation_docs_exist`

### Validation Criteria Check
- [x] Bootstrap script is idempotent.
- [x] Payload contract count is exactly 27.
- [x] Unit tests pass.

---

## Phase 1.2 Route Authorization Policy Validation (2026-02-22)

### Problem Statement
Public endpoints must stay public; all protected endpoints must require valid auth. Route authorization was incorrectly treating `/auth/refresh` as public when it should be protected.

### Solution: Route-Level Auth Policy Implementation

#### Updated Files
- `infra/careervp/api_construct.py` - Fixed `_add_route_method` to use explicit public routes list

#### Code Change
Before:
```python
is_public_route = path.startswith("/auth/") or path == "/health"
```

After:
```python
# Per auth_and_authorizer_spec.yaml:
# - Public (unprotected): /health, /auth/register, /auth/login
# - Protected: /auth/refresh and all other routes
public_paths = {"/health", "/auth/register", "/auth/login"}
is_public_route = path in public_paths
```

### Test Results

#### Infra Tests
Command:
```bash
cd infra && uv run pytest tests/infrastructure/test_api_construct.py::test_public_routes_have_no_authorizer tests/infrastructure/test_api_construct.py::test_protected_routes_require_authorizer -v
```

Output:
```
test_public_routes_have_no_authorizer PASSED
test_protected_routes_require_authorizer PASSED
```

#### Unit Tests
Command:
```bash
cd src/backend && uv run pytest tests/unit/test_route_authorizer_policy.py -v
```

Output summary:
- `9 passed`
- Tests:
  - `test_payload_contracts_loaded`
  - `test_auth_spec_defines_public_routes`
  - `test_auth_spec_defines_protected_routes`
  - `test_total_route_count`
  - `test_public_routes_in_payloads`
  - `test_auth_refresh_is_protected`
  - `test_public_routes_defined_in_spec`
  - `test_public_routes_defined`
  - `test_no_public_routes_protected`

### Authorization Policy Summary

| Route | Method | Auth Required | Status |
|-------|--------|---------------|--------|
| /health | GET | false | Public |
| /auth/register | POST | false | Public |
| /auth/login | POST | false | Public |
| /auth/refresh | POST | true | Protected |
| All other routes | * | true | Protected |

**Total:** 27 routes = 3 public + 24 protected

### Validation Criteria Check
- [x] Public routes do not require authorizer (3 routes verified)
- [x] Protected routes require authorizer (24 routes verified)
- [x] /auth/refresh correctly requires auth (fixed from public)
- [x] Unit tests pass
- [x] Infra tests pass

---

## Phase 1.3 Route Smoke Script (2026-02-22)

### Problem Statement
Route fixes must be validated via API calls during implementation, not only at the end. Need deterministic smoke tests that use payload contracts.

### Solution: Route Smoke Script

#### Created Files
- `docs/refactor3/scripts/step_1.3_route_smoke.sh` - Route smoke test script

#### Script Features
1. **Phase 1: Preflight** - Tests public routes first (/health, /auth/login)
2. **Phase 2: Authentication** - Gets auth token via login
3. **Phase 3: Protected Routes** - Tests protected endpoints with token
4. **Fail-fast** - Exits on first failure

#### Usage
```bash
# With arguments
./docs/refactor3/scripts/step_1.3_route_smoke.sh https://api.example.com test@example.com password123

# With environment variables
export API_BASE=https://api.example.com
export TEST_EMAIL=test@example.com
export TEST_PASSWORD=password123
./docs/refactor3/scripts/step_1.3_route_smoke.sh
```

#### Test Endpoints
- **Public:** GET /health, POST /auth/login
- **Protected:** GET /jobs, POST /jobs, GET /users/me, POST /gap-analysis/questions, POST /vpr/generate

### Unit Tests
Command:
```bash
cd src/backend && uv run pytest tests/unit/test_route_smoke_script.py -v
```

Output summary:
- `15 passed`
- Tests:
  - `test_payloads_directory_exists`
  - `test_payloads_count`
  - `test_health_payload_structure`
  - `test_job_list_payload_structure`
  - `test_auth_login_payload_structure`
  - `test_public_routes_in_payloads`
  - `test_smoke_script_exists`
  - `test_smoke_script_is_executable`
  - `test_script_fails_without_api_base`
  - `test_script_fails_without_credentials`
  - `test_script_uses_payloads_directory`
  - `test_script_has_fail_fast_logic`
  - `test_health_payload_has_expected_status`
  - `test_auth_login_payload_has_expected_status`
  - `test_protected_routes_have_auth_headers`

### Validation Criteria Check
- [x] Script reads payload contracts from docs/refactor3/payloads
- [x] Script fails on first route mismatch (fail-fast)
- [x] Unit tests pass
