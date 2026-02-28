# CareerVP Live Tests

This directory contains end-to-end live tests for the CareerVP API.

## Test Structure

```
live_tests/
├── conftest.py                    # Configuration and shared fixtures
├── run_all_tests.py               # Test runner script
├── README.md                      # This file
├── test_00_auth_bootstrap.py      # Cognito/auth bootstrap validation
├── test_01_auth_health.py         # Health & Auth endpoints
├── test_02_users.py               # User management endpoints
├── test_03_jobs.py                # Job management endpoints
├── test_04_vpr.py                 # VPR (Value Proposition Report) endpoints
├── test_05_gap_analysis.py        # Gap Analysis endpoints
├── test_06_cv_tailoring.py        # CV Tailoring endpoints
├── test_07_cover_letter.py        # Cover Letter endpoints
├── test_08_interview_prep.py      # Interview Prep endpoints
├── test_09_company_research.py    # Company Research endpoints
├── test_10_api_contract_success.py# Strict 27-endpoint contract suite
└── test_11_api_error_contracts.py # Error-contract and new-route live tests
```

## Running Tests

### Using pytest (recommended)

```bash
# Run all tests
pytest docs/refactor/live_tests/ -v

# Run specific test file
pytest docs/refactor/live_tests/test_01_auth_health.py -v

# Run specific test class
pytest docs/refactor/live_tests/test_04_vpr.py::TestVPREndpoints -v

# Run specific test method
pytest docs/refactor/live_tests/test_04_vpr.py::TestVPREndpoints::test_generate_vpr -v
```

### Using the test runner

```bash
# Run all tests
python docs/refactor/live_tests/run_all_tests.py

# Run specific test
python docs/refactor/live_tests/run_all_tests.py --test vpr

# List available tests
python docs/refactor/live_tests/run_all_tests.py --list

# Verbose output
python docs/refactor/live_tests/run_all_tests.py --verbose

# Dry run (show what would run)
python docs/refactor/live_tests/run_all_tests.py --dry-run
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE` | API base URL (resolved from CloudFormation if unset) | (auto) |
| `TEST_USER_ID` | Test user ID | `test-user-e2e` |
| `API_KEY` | API key for authentication | (empty) |
| `USE_AUTH` | Whether to use authentication | `true` |
| `STRICT_AUTH` | Fail (instead of skip) when protected auth bootstrap is unavailable | `false` |
| `COGNITO_REGION` | Cognito region for live JWT auth | (auto from stack) |
| `COGNITO_USER_POOL_ID` | Cognito user pool ID | (auto from stack) |
| `COGNITO_APP_CLIENT_ID` | Cognito app client ID | (auto from stack) |
| `COGNITO_APP_CLIENT_SECRET` | Cognito app client secret (if required) | (empty) |
| `COGNITO_TOKEN_USE` | Token used for bearer auth (`id` or `access`) | `id` |
| `STACK_NAME` | CloudFormation stack for auto-discovery | `CareerVpCrudDev` |

### Example: Run against staging

```bash
API_BASE=https://staging.careervp.com/v1 pytest docs/refactor/live_tests/ -v
```

## Test Coverage

This test suite covers all 27 API endpoints defined in the OpenAPI spec:

| # | Endpoint | Method | Test File |
|---|----------|--------|-----------|
| 1 | `/health` | GET | test_01_auth_health.py |
| 2 | `/auth/register` | POST | test_01_auth_health.py |
| 3 | `/auth/login` | POST | test_01_auth_health.py |
| 4 | `/auth/refresh` | POST | test_01_auth_health.py |
| 5 | `/users/me` | GET | test_02_users.py |
| 6 | `/users/me` | PUT | test_02_users.py |
| 7 | `/users/me/cv` | POST | test_02_users.py |
| 8 | `/users/me/cvs` | GET | test_02_users.py |
| 9 | `/jobs` | POST | test_03_jobs.py |
| 10 | `/jobs` | GET | test_03_jobs.py |
| 11 | `/jobs/{jobId}` | GET | test_03_jobs.py |
| 12 | `/vpr/generate` | POST | test_04_vpr.py |
| 13 | `/vpr/{vprId}` | GET | test_04_vpr.py |
| 14 | `/users/me/vprs` | GET | test_04_vpr.py |
| 15 | `/gap-analysis/questions` | POST | test_05_gap_analysis.py |
| 16 | `/gap-analysis/responses` | POST | test_05_gap_analysis.py |
| 17 | `/gap-analysis/{jobId}/questions` | GET | test_05_gap_analysis.py |
| 18 | `/cv-tailoring/generate` | POST | test_06_cv_tailoring.py |
| 19 | `/cv-tailoring/{cvTailoringId}` | GET | test_06_cv_tailoring.py |
| 20 | `/users/me/tailored-cvs` | GET | test_06_cv_tailoring.py |
| 21 | `/cover-letter/generate` | POST | test_07_cover_letter.py |
| 22 | `/cover-letter/{coverLetterId}` | GET | test_07_cover_letter.py |
| 23 | `/users/me/cover-letters` | GET | test_07_cover_letter.py |
| 24 | `/interview-prep/generate` | POST | test_08_interview_prep.py |
| 25 | `/interview-prep/{interviewPrepId}` | GET | test_08_interview_prep.py |
| 26 | `/company-research/fetch` | POST | test_09_company_research.py |
| 27 | `/company-research/{jobId}` | GET | test_09_company_research.py |
| 28 | `/users/me/usage` | GET | test_11_api_error_contracts.py |
| 29 | `/applications/{application_id}` | GET | test_11_api_error_contracts.py |

## Feature Coverage

The tests also validate the full workflow as specified in the task:

| Feature | Endpoints | Test File |
|---------|-----------|-----------|
| CV Upload | POST /users/me/cv | test_02_users.py |
| Gap Analysis Questions | POST /gap-analysis/questions | test_05_gap_analysis.py |
| Gap Analysis Responses | POST /gap-analysis/responses | test_05_gap_analysis.py |
| VPR Generation | POST /vpr/generate | test_04_vpr.py |
| ATS-Optimized CV | POST /cv-tailoring/generate | test_06_cv_tailoring.py |
| Cover Letter | POST /cover-letter/generate | test_07_cover_letter.py |
| Interview Prep Questions | POST /interview-prep/generate | test_08_interview_prep.py |
| Company Research | POST /company-research/fetch | test_09_company_research.py |

## Test Dependencies

Tests have implicit dependencies on prior test execution:

```
Auth/Login
    ├── User Profile (GET /users/me)
    │   └── CV Upload (POST /users/me/cv)
    │       ├── Gap Analysis Questions (POST /gap-analysis/questions)
    │       │   └── Gap Analysis Responses (POST /gap-analysis/responses)
    │       │       └── VPR Generation (POST /vpr/generate)
    │       │           ├── CV Tailoring (POST /cv-tailoring/generate)
    │       │           └── Cover Letter (POST /cover-letter/generate)
    │       │               └── Interview Prep (POST /interview-prep/generate)
    │       └── Job Creation (POST /jobs)
    │           └── Company Research (POST /company-research/fetch)
```

## Payload Usage

Tests reference payloads from the `docs/refactor/payloads/` directory:

- `phase1_vpr_generator_test.json` - VPR generation
- `phase2_gap_analysis_test.json` - Gap analysis
- `phase3_cv_tailoring_test.json` - CV tailoring
- `phase4_cover_letter_test.json` - Cover letter
- `phase6_interview_prep_test.json` - Interview prep
- `phase8_company_research_test.json` - Company research

## Notes

- Tests accept both sync (200) and async (202) responses
- Some endpoints may return 401/404 in dev environment without full deployment
- Async endpoints include polling logic with timeout
- Test data is shared across test files via module imports
- `test_11_api_error_contracts.py` intentionally triggers error paths aligned to `docs/beta/docs_gaps/api_error_codes.md` (401/400/404/422 scenarios).
- Default `run_all_tests.py` run is a live-success smoke path (`bootstrap`, `health`, `auth`) and should emit 2xx status codes.
- Run protected/full suites explicitly after Cognito auth flow compatibility is confirmed for the deployed app client.
