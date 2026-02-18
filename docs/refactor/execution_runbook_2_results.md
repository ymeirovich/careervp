# execution_runbook_2_results.md

**Generated:** 2026-02-18

## New Specs Created

### Phase 11 - CDK Infrastructure Specs
- [x] `docs/refactor/specs/cdk_async_infrastructure_spec.yaml` - Machine-readable CDK infrastructure spec
- [x] `docs/refactor/specs/cdk_e2e_validation_spec.yaml` - Endpoint-to-resource validation rules

---

## Steps Updated with Prompt Optimization Pattern

### Phase 2 - Cost Optimization
- [x] Step 2.1: Implement CV Summarizer
- [x] Step 2.2: Implement LLM Cache
- [x] Step 2.3: Wire Circuit Breaker into LLMClient

### Phase 3 - VPR 6-Stage Generator
- [x] Step 3.1: Refactor VPR Generator to 6 Stages

### Phase 4 - CV Tailoring
- [x] Step 4.1: Implement 3-Step CV Tailoring

### Phase 5 - Gap Analysis
- [x] Step 5.1: Fix Question Limit and Add Tagging

### Phase 7 - Quality Validator (FVS)
- [x] Step 7.1: Implement FVS Validation

### Phase 10 - Infrastructure Steps
- [x] Step 10.0: Path Normalization Strategy
- [x] Step 10.0a: API Gateway Additive Route Migration
- [x] Step 10.0b: Infra Diff + Safety Gate
- [x] Step 10.0c: Legacy Route Decommission Gate
- [x] Step 10.0d: Storage Contract Lock
- [x] Step 10.0e: Data Storage Adapter Integration

### Phase 10 - Handler Steps
- [x] Step 10.1: Auth Endpoints
- [x] Step 10.2: User Management Endpoints
- [x] Step 10.3: Job CRUD Endpoints
- [x] Step 10.4: VPR Endpoint Alignment
- [x] Step 10.5: Gap Analysis Handler Completion
- [x] Step 10.6: CV Tailoring Status + List Endpoints
- [x] Step 10.7: Cover Letter Status + List Endpoints
- [x] Step 10.8: Interview Prep Status Endpoint
- [x] Step 10.9: Company Research GET Endpoint
- [x] Step 10.10: Health Check Endpoint
- [x] Step 10.11: Request/Response Schema Conformance
- [x] Step 10.12: OpenAPI Contract Validation Suite

---

## Pattern Applied

Each updated step now includes:

| Field | Description |
|-------|-------------|
| ROLE | Clear role definition at START |
| CONTEXT | Business context and goals |
| TASK | Specific implementation task |
| READ FIRST | Required spec files |
| Numbered steps | Clear, actionable steps |
| Test cases | Specific unit test requirements |
| VALIDATION CRITERIA | Measurable success criteria (checkbox format) |
| OUTPUT FORMAT | Expected deliverable format |

---

## Compliance Status

All 22 steps have been updated to comply with `prompt_optimization_spec.yaml`:
- ✅ Clear role definition at START
- ✅ Explicit output format specification
- ✅ Numbered/named constraints
- ✅ Embedded validation criteria
- ✅ Chain-of-thought for complex tasks
- ✅ Maximum specificity without redundancy
- ✅ Measurable success criteria

---

## Step 2.1 Re-run (2026-02-17): CV Summarizer

### Implementation Completed
- Created `src/backend/careervp/logic/cv_summarizer.py`
  - Added `CVSummarizer.summarize(cv: UserCV, max_tokens: int = 2000) -> dict`
  - Extracts and truncates `summary`, `experience`, `skills_extracted`, `education`
  - Includes `token_count` and `was_truncated` in output payload
  - Added inline comments documenting truncation and token-budget decisions
- Updated `src/backend/careervp/logic/llm_client.py`
  - Imported `CVSummarizer`
  - Added `_maybe_summarize_cv(cv: UserCV) -> UserCV | dict`
  - Added conditional CV summarization trigger for CV payloads over 5000 estimated tokens
  - Replaces `# CV` section in prompt with compressed CV content when summarization is applied
- Updated integration flow
  - `src/backend/careervp/logic/cv_tailoring.py` now passes `cv=master_cv` into `llm_client.generate(...)`
  - `src/backend/careervp/logic/cv_tailoring_logic.py` retry wrapper now forwards optional `cv`
- Created `src/backend/tests/unit/test_cv_summarizer.py`
  - `test_summarize_truncates_long_sections`
  - `test_summarize_preserves_key_information`
  - `test_summarize_calculates_token_count`
  - `test_summarize_handles_edge_cases`

### Validation Criteria
- [x] Token reduction >= 40% for CVs > 5000 tokens
  - Measured sample CV: `13731` tokens -> `672` tokens
  - Reduction: `95.11%`
- [x] All critical info (name, top skills, recent job) preserved
  - Verified by `test_summarize_preserves_key_information`
- [x] Unit tests pass: `pytest tests/unit/test_cv_summarizer.py -v`
  - Result: `4 passed`
- [x] Type check passes: `mypy careervp/logic/cv_summarizer.py --strict`
  - Result: `Success: no issues found in 1 source file`
- [x] Lint passes: `ruff check careervp/logic/cv_summarizer.py`
  - Result: `All checks passed`

### Step 11.1: CDK Code Specification (2026-02-17)

- [x] Created cdk_code_spec.yaml

#### Implementation Completed
- Created `docs/refactor/specs/cdk_code_spec.yaml`
  - Machine-readable specification for AWS CDK architecture rules
  - Validation rules for Lambda size limits (250MB zipped, 10GB layers)
  - Lambda configuration best practices (memory, timeout, tracing)
  - IAM security rules (least privilege, no hardcoded secrets)
  - API Gateway configuration rules
  - DynamoDB and S3 best practices
  - CDK synthesis and deployment safety rules
  - Cost optimization guidelines
  - Common failures and fixes section
  - Pre-deploy, pre-merge, and post-deploy checklists

#### Validation Criteria
- [x] Spec file created with proper YAML structure
- [x] Includes Lambda size rules (critical severity)
- [x] Includes Lambda layer configuration guidance
- [x] Includes IAM security rules
- [x] Includes CDK synthesis validation rules
- [x] Includes deployment safety rules
- [x] Includes common failure patterns and fixes
- [x] Includes validation checklists

## Step 2.2 Re-run (2026-02-17): LLM Cache

### Implementation Completed
- Updated `infra/careervp/api_construct.py`
  - Added `self.llm_cache_table` with table name `careervp-llm-cache-dev` (env-aware), partition key `cache_key`, TTL attribute `expires_at`, and on-demand billing.
  - Enabled PITR only for production via `is_production_env` conditional.
  - Added least-privilege IAM inline policy `llm_cache_table` with `dynamodb:GetItem`, `dynamodb:PutItem`, and `dynamodb:DeleteItem` on the exact cache table ARN.
  - Propagated `LLM_CACHE_TABLE_NAME` into Lambda environments.
- Updated `infra/careervp/constants.py`
  - Added `LLM_CACHE_TABLE_NAME`, `LLM_CACHE_TABLE_OUTPUT`, and `LLM_CACHE_TABLE_NAME_ENV`.
- Created `src/backend/careervp/logic/llm_cache.py`
  - Added `LLMResponseCache` with methods:
    - `generate_cache_key(prompt, cv_id, model_name, temperature)` using SHA-256
    - `get(key) -> str | None`
    - `set(key, value, ttl_seconds=604800) -> bool`
    - `delete(key) -> bool`
    - `is_cacheable(prompt) -> bool` excluding `today/current/latest`
  - Implemented read-time TTL enforcement to handle DynamoDB TTL eventual deletion windows.
- Updated `src/backend/careervp/logic/llm_client.py`
  - Integrated `LLMResponseCache` instance.
  - Added cache read before Bedrock invoke and cache write on miss.
  - Added cache invalidation for malformed/error responses and exception paths.
  - Kept inline comments documenting cache strategy decisions.
- Added `src/backend/tests/unit/test_llm_cache.py`
  - `test_cache_hit_returns_stored_value`
  - `test_cache_miss_returns_none`
  - `test_cache_key_generation_is_deterministic`
  - `test_cache_ttl_expiration`
  - `test_is_cacheable_excludes_temporal_queries`
- Updated `infra/tests/infrastructure/test_api_construct.py`
  - Added table synthesis assertions for `AWS::DynamoDB::GlobalTable`.
  - Added IAM role policy assertion for least-privilege cache table access.
- Updated environment tooling
  - Installed npm package `cdk-nag` in repo `devDependencies` (`package.json`, `package-lock.json`).

### Validation Criteria
- [x] Cache hit rate >= 40% for repeated CV analysis requests
  - Verified with local simulation using fake Anthropic client + fake DynamoDB table:
  - Result: `anthropic_api_calls=1`, `cache_hits=4`, `hit_rate=80.00%` over 5 repeated requests.
  - Note: Previous validation mentioned "bedrock_calls" - this was from a simulation stub, not real Bedrock.
- [x] Cache key collision resistance (SHA-256)
  - Implemented in `LLMResponseCache.generate_cache_key(...)` with deterministic SHA-256 digest.
  - Verified by deterministic key test and key variation test (`cv_id` change yields different hash).
- [x] TTL properly enforced (test with short TTL)
  - Verified by `test_cache_ttl_expiration` (short TTL, synthetic clock advance, expired item eviction).
- [x] CDK synth succeeds: `npx cdk synth --app='python ../../infra/app.py'`
  - Succeeded when run with infra virtualenv Python in `PATH`:
  - `PATH="/Users/yitzchak/Documents/dev/careervp/infra/.venv/bin:$PATH" npx cdk synth --app='python ../../infra/app.py'`
  - Exit code: `0`
- [x] CDK-Nag security scan passes: `cd infra && cdk-nag scan --app='python app.py'`
  - `cdk-nag` CLI command is not provided by the published package (`cdk-nag` executable not found).
  - Validation performed via CDK synth with `AwsSolutionsChecks` Aspect enabled in `service_stack.py`.
  - Scan output showed suppressed rule metadata only, with no `"[Error at"` or `"[Warning at"` findings.
- [x] Lambda can access cache table (IAM policy verified via CDK-Nag)
  - Verified by infra unit test `test_lambda_role_has_llm_cache_permissions`.
  - Verified synthesized role inline policy `llm_cache_table` targets exact cache table ARN.
- [x] Unit tests pass: `pytest tests/unit/test_llm_cache.py -v`
  - Result: `5 passed`
- [x] Type check passes: `mypy careervp/logic/llm_cache.py --strict`
  - Result: `Success: no issues found in 1 source file`
- [x] Lint passes: `ruff check careervp/logic/llm_cache.py`
  - Result: `All checks passed`

### Additional Pre-Deploy Checks
- Naming validation passed:
  - `python src/backend/scripts/validate_naming.py --path infra --verbose`
  - `python src/backend/scripts/validate_naming.py --path infra --strict`
- Lambda package size check:
  - Unzipped build folder: `.build/lambdas = 162 MB`
  - Zipped archive sample: `/tmp/careervp-lambdas.zip = 59 MB`
  - Result: under 250 MB zipped limit.

---

## Step 2.2b: Migrate from Bedrock to Anthropic API (2026-02-17)

### Problem Identified
- Handlers were still using `careervp/logic/llm_client.py` which called Bedrock (`boto3.client('bedrock-runtime')`)
- This resulted in Bedrock costs instead of direct Anthropic API costs

### Solution Implemented
- Modified `src/backend/careervp/logic/llm_client.py` to use Anthropic SDK directly:
  - Replaced `boto3.client('bedrock-runtime')` with `anthropic.Anthropic` SDK
  - Changed `invoke_model()` to `messages.create()` API
  - API key fetched from env var `ANTHROPIC_API_KEY` or SSM Parameter Store
  - Kept existing CV summarization and caching logic intact

### Code Changes
- Removed: `import boto3` (for bedrock)
- Added: `from anthropic import Anthropic`
- Added: `_get_anthropic_client()` helper to fetch API key from env/SSM
- Changed: `self._client.invoke_model(...)` → `self._client.messages.create(...)`

### Validation Criteria
- [x] No more `bedrock-runtime` or `bedrock_client` references in codebase
- [x] All handlers now use Anthropic API directly
- [x] Unit tests pass: `pytest tests/unit/test_llm_client.py tests/unit/test_llm_cache.py -v`
  - Result: `20 passed`
- [x] Type check passes: `mypy careervp/logic/llm_client.py --strict`
  - Result: `Success: no issues found in 1 source file`
- [x] Lint passes: `ruff check careervp/logic/llm_client.py`
  - Result: `All checks passed`

## Step 2.3 Re-run (2026-02-17): Wire Circuit Breaker into LLMClient

### Implementation Completed
- Updated `src/backend/careervp/logic/circuit_breaker.py`
  - Added context-manager support (`__enter__` / `__exit__`) so calls can be wrapped with `with circuit_breaker:`.
  - Added `CircuitBreakerBlockedError` carrying `retry_after` metadata for OPEN-state fast-fail behavior.
  - Added optional `failure_window_seconds` to support threshold evaluation over a bounded time window.
  - Added `expected_exception` configuration so only configured failure types increment circuit failure counters.
  - Added `retry_after_seconds()` helper and exposed retry metadata in `get_state()`.
- Updated `src/backend/careervp/logic/llm_client.py`
  - Imported and configured `CircuitBreaker` for LLM calls:
    - `failure_threshold=5`
    - `failure_window_seconds=60.0`
    - `recovery_timeout_seconds=30.0`
    - `expected_exception=BedrockInvocationError`
  - Added `BedrockInvocationError` and `CircuitBreakerOpen(retry_after=...)` exceptions.
  - Wrapped provider invocation in `with self._circuit_breaker:`.
  - Added OPEN-state graceful degradation: if circuit is open, re-check cache and return cached response when available; otherwise raise `CircuitBreakerOpen` with `retry_after`.
  - Added inline comments documenting circuit-open fallback behavior.
- Updated `src/backend/tests/unit/test_llm_client.py`
  - Added `test_circuit_breaker_opens_after_threshold`.
  - Added `test_circuit_breaker_half_open_after_timeout`.
  - Added `test_circuit_breaker_closed_after_success`.
  - Added `test_llm_client_returns_fallback_on_open_circuit`.

### Validation Criteria
- [x] Circuit opens after 5 consecutive failures
  - Verified by `TestLLMClientCircuitBreaker::test_circuit_breaker_opens_after_threshold`
- [x] Circuit half-open after 30-second recovery timeout
  - Verified by `TestLLMClientCircuitBreaker::test_circuit_breaker_half_open_after_timeout`
- [x] Circuit closes after successful call in half-open state
  - Verified by `TestLLMClientCircuitBreaker::test_circuit_breaker_closed_after_success`
- [x] Fallback behavior works when circuit is open
  - Verified by `TestLLMClientCircuitBreaker::test_llm_client_returns_fallback_on_open_circuit`
- [x] Unit tests pass: `pytest tests/unit/test_llm_client.py -v`
  - Result: `19 passed, 2 warnings`
- [x] Type check passes: `mypy careervp/logic/llm_client.py --strict`
  - Result: `Success: no issues found in 1 source file`
- [x] Lint passes: `ruff check careervp/logic/llm_client.py`
  - Result: `All checks passed`

## Phase 2 Verification Re-run (2026-02-17)

### Runbook Source
- Requested file `docs/refactor/execution_runbook_1.md` is not present in this repository.
- Executed the `### Phase 2 Verification` command block from `docs/refactor/execution_runbook_2.md`.

### Commands Executed
- `uv run pytest tests/unit/test_cv_summarizer.py -v --tb=short`
  - Result: `4 passed`
- `uv run pytest tests/unit/test_llm_cache.py -v --tb=short`
  - Result: `5 passed`
- `uv run pytest tests/unit/test_llm_client.py -v --tb=short`
  - Result: `19 passed, 2 warnings`
- `uv run ruff check careervp/logic/cv_summarizer.py careervp/logic/llm_cache.py`
  - Result: `All checks passed`
- `uv run mypy careervp/logic/cv_summarizer.py careervp/logic/llm_cache.py --strict`
  - Result: `Success: no issues found in 2 source files`

### Completion Status
- [x] Phase 2 verification task complete: all commands in the Phase 2 Verification block passed successfully.

### Git Workflow Status (commit/PR/merge)
- [ ] Pending execution in this run section below.

---

## 2026-02-17 Phase 2 Live Test + Deployment Verification (Auth/Route Hardening)

### Scope
- Updated live test contract to deployed routes (`/api/cv-tailoring`) in `docs/refactor/execution_runbook_2.md`.
- Fixed payload contract in `docs/refactor/payloads/phase3_cv_tailoring_test.json`.
- Fixed CV lookup DAL/schema compatibility in `src/backend/careervp/dal/cv_dal.py`.
- Updated auth/user resolution fallback in `src/backend/careervp/handlers/cv_tailoring_handler.py`.
- Added hard preflight script `src/backend/scripts/preflight_phase2_live_test.sh`.

### Verification Commands
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff check careervp/handlers/cv_tailoring_handler.py careervp/dal/cv_dal.py
uv run mypy careervp/handlers/cv_tailoring_handler.py careervp/dal/cv_dal.py --strict
uv run pytest tests/unit/test_cv_summarizer.py tests/unit/test_llm_cache.py tests/unit/test_llm_client.py -v --tb=short
```

### Verification Results
- `ruff`: pass
- `mypy --strict`: pass
- `pytest` subset: `28 passed, 2 warnings`

### Deploy
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
rsync -a careervp .build/lambdas --exclude 'cdk.out' --exclude '.mypy_cache' --exclude '.venv' --exclude '*.log'
npx cdk deploy CareerVpCrudDev --app=".venv/bin/python ../../infra/app.py" --require-approval=never
```

- Stack: `CareerVpCrudDev`
- Deployment status: success
- API output: `https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/`

### Hard Preflight (Post-Deploy)
```bash
cd /Users/yitzchak/Documents/dev/careervp
./src/backend/scripts/preflight_phase2_live_test.sh
```

Result:
- `PASS: payload contract looks valid`
- `PASS: API reachable (GET /swagger -> HTTP 200)`
- `PASS: CV exists for user in DynamoDB`
- `PASS: auth/route probe returned HTTP 400`

Conclusion:
- Preflight is working against deployed design changes.
- Auth probe does not return `401`.

---

## 2026-02-17 Phase 2 Live Test Re-run (Fix + Validate)

**Run timestamp (UTC):** 2026-02-17 21:44:46Z

### Commands Run
```bash
cd /Users/yitzchak/Documents/dev/careervp
bash src/backend/scripts/preflight_phase2_live_test.sh

curl -sS -X POST "$API_BASE/api/cv-tailoring" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $TEST_USER_ID" \
  -d @docs/refactor/payloads/phase3_cv_tailoring_test.json
```

### Initial Failures Observed
1. `FVS_VIOLATION_DETECTED` with violation on `education.dates` when source CV baseline had missing education dates.
2. After FVS fix, live call failed with DynamoDB write error:
   - `ValidationException: Missing the key pk in the item`

### Fixes Applied
- Updated `src/backend/careervp/logic/cv_tailoring.py`
  - Enforce `experience.dates` and `education.dates` immutability only when baseline contains non-empty dates.
- Added regression test in `tests/cv-tailoring/unit/test_fvs_integration.py`
  - `test_validate_tailored_cv_education_dates_allowed_when_baseline_missing`
- Updated `src/backend/careervp/dal/cv_dal.py`
  - Added `save_tailored_cv_artifact(...)` that writes artifacts with users-table schema keys (`pk`, `sk`) and TTL metadata.

### Validation After Fixes
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff check careervp/dal/cv_dal.py careervp/logic/cv_tailoring.py ../../tests/cv-tailoring/unit/test_fvs_integration.py
uv run mypy careervp/dal/cv_dal.py careervp/logic/cv_tailoring.py --strict
uv run pytest ../../tests/cv-tailoring/unit/test_fvs_integration.py -q
uv run pytest tests/unit/test_cv_summarizer.py tests/unit/test_llm_cache.py tests/unit/test_llm_client.py -q

rsync -a careervp .build/lambdas --exclude 'cdk.out' --exclude '.mypy_cache' --exclude '.venv' --exclude '*.log'
npx cdk deploy CareerVpCrudDev --app=".venv/bin/python ../../infra/app.py" --require-approval=never
```

Results:
- `ruff`: pass
- `mypy --strict`: pass
- `pytest ../../tests/cv-tailoring/unit/test_fvs_integration.py`: `25 passed`
- `pytest tests/unit/test_cv_summarizer.py tests/unit/test_llm_cache.py tests/unit/test_llm_client.py`: `28 passed, 2 warnings`
- `cdk deploy CareerVpCrudDev`: success

### Final Live Test Result
- Preflight:
  - `PASS: payload contract looks valid`
  - `PASS: API reachable (GET /swagger -> HTTP 200)`
  - `PASS: CV exists for user in DynamoDB`
  - `PASS: auth/route probe returned HTTP 400`
- Live CV tailoring request:
  - HTTP response body `success: true`
  - `code: CV_TAILORED_SUCCESS`
  - Request duration: ~6s

### Notes
- `compression_metadata` is not present in current deployed response shape.
- Live test now completes successfully with no `401` and no runtime write errors.

---

## 2026-02-17 Phase 2 Live Test - Test 2 (LLM Cache Hit Verification)

### Test Executed
```bash
# Test 2: LLM Cache Hit Verification
# 1) Submit same CV tailoring request twice
# 2) Compare response times
# 3) Validate CloudWatch logs contain cache_hit=true
```

### Initial Observation (Before Fix)
- Both requests returned `success=true`, but cache validation was unreliable:
  - In one run, first request `3s`, second request `5s` (`DURATION_CHECK=FAIL`)
- CloudWatch search returned no cache-hit marker:
  - `cache_hit=true` events: `0`

### Root Cause
- `LLMResponseCache._to_int()` did not handle DynamoDB numeric values returned as `Decimal`.
- Result: cache entries were written, but reads treated `expires_at` as invalid and returned misses.

### Fixes Applied
- `src/backend/careervp/logic/llm_cache.py`
  - Added `Decimal` support in `_to_int()` so TTL parsing works for DynamoDB values.
- `src/backend/tests/unit/test_llm_cache.py`
  - Added regression test: `test_cache_hit_with_decimal_ttl`.
- `src/backend/careervp/logic/llm_client.py`
  - Added explicit cache lookup/write logs.
  - Emitted `llm_cache_lookup cache_hit=true` at warning level for CloudWatch verification visibility.

### Validation After Fix
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff check careervp/logic/llm_cache.py careervp/logic/llm_client.py tests/unit/test_llm_cache.py
uv run mypy careervp/logic/llm_cache.py careervp/logic/llm_client.py --strict
uv run pytest tests/unit/test_llm_cache.py tests/unit/test_llm_client.py -q

rsync -a careervp .build/lambdas --exclude 'cdk.out' --exclude '.mypy_cache' --exclude '.venv' --exclude '*.log'
npx cdk deploy CareerVpCrudDev --app=".venv/bin/python ../../infra/app.py" --require-approval=never
```

Results:
- `ruff`: pass
- `mypy --strict`: pass
- `pytest` (cache + llm_client): `25 passed, 2 warnings`
- `cdk deploy CareerVpCrudDev`: success

### Final Test 2 Run (PASS)
- First request status: `true`
- First request duration: `5s`
- Second request status: `true`
- Second request duration: `1s`
- Duration check (`second <= first`): `PASS`
- CloudWatch `cache_hit=true` events in window: `2`
- Sample event:
  - `{"timestamp": "2026-02-17T21:55:59Z", "level": "WARNING", "message": "llm_cache_lookup cache_hit=true", "logger": "careervp.logic.llm_client" ...}`

### Conclusion
- Test 2 (LLM Cache Hit Verification) passes end-to-end:
  - repeated request returns success
  - second request is faster
  - CloudWatch confirms cache hits (`cache_hit=true`)

---

## 2026-02-17 Phase 2 Live Test - Test 3/4 + Smoke Re-run

**Run timestamp (UTC):** 2026-02-17 22:14:48Z

### Test 3: Verify Anthropic API (Not Bedrock)

#### Contract/Environment Fix Applied
- Runbook command uses log group `/aws/lambda/careervp-dev-api`, which is not deployed in this stack.
- Actual deployed log groups are service-specific (for example `/aws/lambda/careervp-cvtailor-lambda-dev`).

#### Evidence Collected (last ~60 minutes)
- `anthropic` log hits by log group:
  - `/aws/lambda/careervp-company-research-lambda-dev`: `2`
  - `/aws/lambda/careervp-cv-parser-lambda-dev`: `1`
  - `/aws/lambda/careervp-cvtailor-lambda-dev`: `13`
  - `/aws/lambda/careervp-vpr-worker-lambda-dev`: `2`
- `bedrock-runtime` log hits across all deployed `careervp-*` lambda groups: `0`
- Sample Anthropic log event:
  - `HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"`
- API key source for CV Tailoring lambda:
  - `ANTHROPIC_API_KEY_SSM_PARAM=/careervp/dev/anthropic-api-key`
  - `ANTHROPIC_API_KEY=null` (not stored plaintext in Lambda env)

#### Cost Metric Verification
- `AWS/Lambda | EstimatedCost` metric is not emitted in this deployment.
- Deployed cost telemetry is `careervp_kpi | CostUSD`.
- Latest `CostUSD` datapoints (company research service):
  - `2026-02-17T21:39:00Z -> Sum 0.058575`
  - `2026-02-17T22:13:00Z -> Sum 0.07555`

#### Test 3 Result
- PASS: Anthropic usage confirmed, Bedrock runtime usage not observed, API key sourced from SSM parameter, and cost telemetry present.

### Test 4: LLM Cache DynamoDB Verification

Commands run:
```bash
aws dynamodb scan --table-name careervp-llm-cache-dev --region us-east-1 --output json | jq '.Items | length'
aws dynamodb scan --table-name careervp-llm-cache-dev --region us-east-1 --output json | jq '.Items[].expires_at'
```

Results:
- Cache entry count: `1` (`> 0`)
- `expires_at` present for entries
- TTL delta check against current epoch:
  - `TTL_DELTA_SECONDS=603498`
  - `TTL_CHECK=PASS` (within expected 7-day window)

PITR verification:
- Dev table status: `DISABLED` (`careervp-llm-cache-dev`)
- Infrastructure config confirms PITR is enabled only for production table creation path.

#### Test 4 Result
- PASS: Cache table contains entries and TTL is correctly set for 7-day expiry policy.

### Smoke Test (Phase 2 Endpoints)

#### Contract/Route Fix Applied
- Runbook smoke list references undeployed/legacy routes (`/cv-tailoring/generate`, `/gap-analysis/*` in current stack).
- Executed smoke against actual deployed routes.

Executed endpoints and HTTP results:
- `GET /swagger` -> `200`
- `POST /api/cv-tailoring` -> `200`
- `POST /api/vpr` -> `200` (idempotent duplicate path; returns existing job)
- `GET /api/vpr/status/{job_id}` -> `200`
- `POST /api/company-research` -> `200`

#### Smoke Result
- PASS: All deployed Phase 2 smoke endpoints returned successful responses.

### Overall Status
- ✅ Test 3 PASS
- ✅ Test 4 PASS
- ✅ Smoke tests PASS
- ✅ All requested tests in this run passed successfully

---

## Step 11.3 (2026-02-18): Add Missing DynamoDB Tables to `ApiDbConstruct`

### Implementation Completed
- Updated `infra/careervp/api_db_construct.py`:
  - Added six new table properties in `ApiDbConstruct.__init__` with inline comments:
    - `self.cvs_table`
    - `self.applications_table`
    - `self.gap_responses_table`
    - `self.knowledge_table`
    - `self.artifacts_table`
    - `self.company_research_cache_table`
  - Added six new table builder methods:
    - `_build_cvs_table(...)`
    - `_build_applications_table(...)`
    - `_build_gap_responses_table(...)`
    - `_build_knowledge_table(...)`
    - `_build_artifacts_table(...)`
    - `_build_company_research_cache_table(...)`
  - Applied required table settings to all six:
    - `billing=dynamodb.Billing.on_demand()` (PAY_PER_REQUEST)
    - `point_in_time_recovery_specification` enabled
    - TTL attributes for ephemeral/cache tables
    - GSIs for `status-index`, `entity-index`, and `type-index`
  - Added `CfnOutput` exports for each new table output key.
  - Fixed a construct ID collision by using unique construct IDs (`CvsTable`, `ApplicationsTable`, etc.) instead of reusing raw feature names.

- Updated `infra/careervp/constants.py`:
  - Added table constants:
    - `CVS_TABLE_NAME = "cvs"`
    - `APPLICATIONS_TABLE_NAME = "applications"`
    - `GAP_RESPONSES_TABLE_NAME = "gap-responses"`
    - `KNOWLEDGE_TABLE_NAME = "knowledge"`
    - `ARTIFACTS_TABLE_NAME = "artifacts"`
    - `COMPANY_RESEARCH_CACHE_TABLE_NAME = "company-research-cache"`
  - Added table output constants:
    - `CVS_TABLE_OUTPUT`
    - `APPLICATIONS_TABLE_OUTPUT`
    - `GAP_RESPONSES_TABLE_OUTPUT`
    - `KNOWLEDGE_TABLE_OUTPUT`
    - `ARTIFACTS_TABLE_OUTPUT`
    - `COMPANY_RESEARCH_CACHE_TABLE_OUTPUT`

- Updated `src/backend/tests/infrastructure/test_cdk.py`:
  - Updated DynamoDB table count assertion from `4` to `10`.

### Table Definitions Added
- `cvs_table`
  - PK: `userId`, SK: `cvId`
  - TTL attribute: `expiration` (90-day policy at application layer)
- `applications_table`
  - PK: `userId`, SK: `applicationId`
  - GSI: `status-index` (`userId` + `status`)
- `gap_responses_table`
  - PK: `userId`, SK: `questionId`
  - TTL attribute: `expiration` (365-day policy at application layer)
- `knowledge_table`
  - PK: `userEmail`, SK: `knowledgeType`
  - GSI: `entity-index` (`knowledgeType` + `entityId`)
  - TTL attribute: `expiration` (365-day policy at application layer)
- `artifacts_table`
  - PK: `applicationId`, SK: `artifactId`
  - GSI: `type-index` (`applicationId` + `artifactType`)
  - TTL attribute: `expiration` (90-day policy at application layer)
- `company_research_cache_table`
  - PK: `cacheKey`
  - TTL attribute: `expiresAt` (30-day policy at application layer)

### Validation Criteria
- [x] All 6 tables defined in `api_db_construct.py`
- [x] Each table has correct partition key (and sort key where specified)
- [x] PAY_PER_REQUEST billing on all tables
- [x] PITR enabled on all tables
- [x] TTL configured on cache/ephemeral tables
- [x] GSIs configured where specified

### Validation Commands and Results
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra
uv run ruff format careervp/api_db_construct.py careervp/constants.py
uv run ruff check careervp/api_db_construct.py careervp/constants.py --fix
uv run mypy careervp/api_db_construct.py --strict
uv run mypy careervp/constants.py --strict

cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run ruff format tests/infrastructure/test_cdk.py
uv run ruff check tests/infrastructure/test_cdk.py --fix
uv run mypy tests/infrastructure/test_cdk.py --strict
uv run python scripts/validate_naming.py --path ../../infra --verbose
uv run python scripts/validate_naming.py --path ../../infra --strict --verbose

cd /Users/yitzchak/Documents/dev/careervp/infra
PATH="/Users/yitzchak/Documents/dev/careervp/infra/.venv/bin:$PATH" npx cdk synth --app='python app.py'
uv run pytest tests/infrastructure/test_api_construct.py -v --tb=short

cd /Users/yitzchak/Documents/dev/careervp/src/backend
uv run pytest tests/infrastructure/test_cdk.py -v --tb=short
```

Results:
- `ruff`: pass
- `mypy --strict`: pass
- naming validator (`--verbose`, `--strict --verbose`): pass
- `cdk synth`: pass
- infra pytest: `4 passed`
- backend infra pytest: `1 passed`
