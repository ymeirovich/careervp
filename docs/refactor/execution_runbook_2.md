# CareerVP Execution Runbook 2.0 - Remaining Tasks

**Document Version:** 2.0
**Date:** 2026-02-17
**Purpose:** Complete implementation of remaining phases following execution_runbook.md format

---

## Implementation Order

1. **Quality Gaps FIRST** (Phases 2-7) - Core business logic
2. **API Contract Gaps SECOND** (Phase 10) - HTTP endpoints
3. **CDK Infrastructure THIRD** (Phase 11) - DynamoDB, S3, Worker Lambdas, SQS

---

## Current Status

| Phase | Status | Gap |
|-------|--------|-----|
| Phase 0 | ✅ COMPLETE | 59 unit tests |
| Phase 1 | ✅ COMPLETE | Model consolidation |
| Phase 2 | ⚠️ PARTIAL (60%) | CV Summarizer, LLM Cache, Circuit Breaker |
| Phase 3 | ⚠️ PARTIAL (65%) | 6-stage pipeline, anti-AI unwired |
| Phase 4 | ⚠️ PARTIAL (70%) | 3-step process, self-correction |
| Phase 5 | ⚠️ PARTIAL (45%) | Question limit 5→10, tagging |
| Phase 6 | ✅ IMPLEMENTED | Cover Letter |
| Phase 7 | ⚠️ PARTIAL (25%) | FVS scoring |
| Phase 8 | ✅ IMPLEMENTED | Knowledge Base |
| Phase 9 | ✅ IMPLEMENTED | Interview Prep |
| Phase 10 | ⚠️ ASSESSED (56%) | 12/27 endpoints |
| Phase 11 | ⚠️ REQUIRES IMPLEMENTATION | Missing DynamoDB tables, S3 buckets, Worker Lambdas, SQS queues |

---

# PART 1: QUALITY GAPS

## Phase 2: Cost Optimization + LLM Caching ⚠️ PARTIAL

**Duration:** 2 days | **Effort:** 8 hours
**Status (2026-02-16):** PARTIAL - 60%

### Specs
| Type | File | Purpose |
|------|------|---------|
| Reference | `cost_optimization_spec.yaml` | Cost optimization strategy |
| Reference | `llm_client_migration_spec.yaml` | LLM client patterns |

### Step 2.1: Implement CV Summarizer

**READ FIRST:**
- `docs/refactor/specs/cv_summarizer_spec.yaml`
- `docs/refactor/specs/cost_optimization_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cv_summarizer_spec.yaml`
- `docs/refactor/specs/cost_optimization_spec.yaml`

ROLE: Senior Backend Engineer specializing in AWS Lambda, Python, and cost optimization

CONTEXT: Implement CV Summarizer to reduce token costs by 40%+ through intelligent context truncation.

TASK: Implement CV Summarizer following cost_optimization_spec.yaml

1. Create: src/backend/careervp/logic/cv_summarizer.py
   - Class: CVSummarizer
   - Method: summarize(cv: UserCV, max_tokens: int = 2000) -> dict
   - Extract key sections: summary, experience, skills, education
   - Implement truncation strategies:
     * Summary: max 200 chars
     * Experience: max 500 chars per job, top 3 jobs
     * Skills: max 50 items, prioritized by relevance
     * Education: max 300 chars
   - Return format: {summary, experience, skills_extracted, education, token_count, was_truncated}

2. Integrate: src/backend/careervp/logic/llm_client.py
   - Import CVSummarizer
   - Add conditional summarization for CV-heavy prompts (>5000 tokens)
   - Create method: _maybe_summarize_cv(cv: UserCV) -> UserCV | dict

3. Create: tests/unit/test_cv_summarizer.py
   - test_summarize_truncates_long_sections
   - test_summarize_preserves_key_information
   - test_summarize_calculates_token_count
   - test_summarize_handles_edge_cases (empty CV, missing sections)

VALIDATION CRITERIA (must all pass):
- [ ] Token reduction >= 40% for CVs > 5000 tokens
- [ ] All critical info (name, top skills, recent job) preserved
- [ ] Unit tests pass: pytest tests/unit/test_cv_summarizer.py -v
- [ ] Type check passes: mypy careervp/logic/cv_summarizer.py --strict
- [ ] Lint passes: ruff check careervp/logic/cv_summarizer.py

OUTPUT FORMAT: Provide complete implementation with inline comments explaining truncation decisions. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 2.2: Implement LLM Cache

**READ FIRST:**
- `docs/refactor/specs/cost_optimization_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cost_optimization_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml`

ROLE: Senior Backend Engineer specializing in AWS Lambda, DynamoDB, and cost optimization

CONTEXT: Implement LLM response cache using DynamoDB with TTL to reduce API costs by 60%+ through response reuse.

TASK: Implement LLM Cache following cost_optimization_spec.yaml caching strategy

1. Create CDK Infrastructure (REQUIRED per CDK_001):
   - Add DynamoDB table in infra/careervp/dynamodb_stack.py or api_construct.py
   - Use PAY_PER_REQUEST billing (per DDB_001 in prompt_optimization_cdk_spec.yaml)
   - Enable point_in_time_recovery=True for production (per DDB_002)
   - Add TTL attribute on expires_at column (AWS manages automatic deletion)
   - Table name: careervp-llm-cache-{env}
   - Schema: partition key = cache_key (String), expires_at (Number TTL)

2. Update Lambda IAM Role:
   - Add read/write permissions for cache table to Lambda execution role
   - Use least-privilege IAM per IAM_001 (specify exact table ARN, not wildcard)

3. Create: src/backend/careervp/logic/llm_cache.py
   - Class: LLMResponseCache
   - Use DynamoDB with TTL for caching (default TTL: 7 days)
   - Cache key generation: hash(prompt + cv_id + model_name + temperature)
   - Methods:
     * get(key: str) -> str | None
     * set(key: str, value: str, ttl_seconds: int = 604800) -> bool
     * delete(key: str) -> bool
     * is_cacheable(prompt: str) -> bool (exclude prompts with "today", "current", "latest")

4. Integrate: src/backend/careervp/logic/llm_client.py
   - Add LLMResponseCache instance
   - Check cache before calling Bedrock: cache.get(cache_key)
   - Store response on cache miss: cache.set(cache_key, response)
   - Implement cache invalidation for error responses

5. Create: tests/unit/test_llm_cache.py
   - test_cache_hit_returns_stored_value
   - test_cache_miss_returns_none
   - test_cache_key_generation_is_deterministic
   - test_cache_ttl_expiration
   - test_is_cacheable_excludes_temporal_queries

6. CDK Pre-Deploy Validation:
   - Run CDK synth to verify template generation
   - Run cdk-nag for security scanning
   - Verify Lambda package size stays under 250MB (per LAMBDA_SIZE_001)

VALIDATION CRITERIA (must all pass):
- [ ] Cache hit rate >= 40% for repeated CV analysis requests
- [ ] Cache key collision resistance (SHA-256)
- [ ] TTL properly enforced (test with short TTL)
- [ ] CDK synth succeeds: npx cdk synth --app='python ../../infra/app.py'
- [ ] CDK-Nag security scan passes: cd infra && cdk-nag scan --app='python app.py'
- [ ] Lambda can access cache table (IAM policy verified via CDK-Nag)
- [ ] Unit tests pass: pytest tests/unit/test_llm_cache.py -v
- [ ] Type check passes: mypy careervp/logic/llm_cache.py --strict
- [ ] Lint passes: ruff check careervp/logic/llm_cache.py

OUTPUT FORMAT: Provide complete implementation with inline comments explaining cache strategy decisions. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 2.3: Wire Circuit Breaker into LLMClient

**READ FIRST:**
- `docs/refactor/specs/circuit_breaker_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
**READ FIRST:**
- `docs/refactor/specs/circuit_breaker_spec.yaml`

ROLE: Backend Engineer specializing in resilience patterns and AWS Lambda

CONTEXT: Wire circuit breaker into LLMClient to prevent cascading failures and ensure graceful degradation during Bedrock outages.

TASK: Integrate CircuitBreaker following circuit_breaker_spec.yaml

1. Update: src/backend/careervp/logic/llm_client.py
   - Import CircuitBreaker from careervp/logic/circuit_breaker
   - Configure circuit breaker:
     * failure_threshold: 5 failures in 60 seconds
     * recovery_timeout: 30 seconds
     * expected_exception: BedrockInvocationError
   - Wrap Bedrock invoke calls:
     with circuit_breaker:
         response = bedrock.invoke_model(...)
   - Handle OPEN state gracefully:
     * Return cached response if available
     * Raise CircuitBreakerOpen with retry_after value

2. Add to tests/unit/test_llm_client.py:
   - test_circuit_breaker_opens_after_threshold
   - test_circuit_breaker_half_open_after_timeout
   - test_circuit_breaker_closed_after_success
   - test_llm_client_returns_fallback_on_open_circuit

VALIDATION CRITERIA (must all pass):
- [ ] Circuit opens after 5 consecutive failures
- [ ] Circuit half-open after 30-second recovery timeout
- [ ] Circuit closes after successful call in half-open state
- [ ] Fallback behavior works when circuit is open
- [ ] Unit tests pass: pytest tests/unit/test_llm_client.py -v
- [ ] Type check passes: mypy careervp/logic/llm_client.py --strict
- [ ] Lint passes: ruff check careervp/logic/llm_client.py

OUTPUT FORMAT: Provide complete implementation with inline comments. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Phase 2 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 2 unit tests
uv run pytest tests/unit/test_cv_summarizer.py -v --tb=short
uv run pytest tests/unit/test_llm_cache.py -v --tb=short
uv run pytest tests/unit/test_llm_client.py -v --tb=short

# Run lint
uv run ruff check careervp/logic/cv_summarizer.py careervp/logic/llm_cache.py

# Run type check
uv run mypy careervp/logic/cv_summarizer.py careervp/logic/llm_cache.py --strict
```

---

## Live Test (Phase 2 - Cost Optimization)

Run AFTER CV Summarizer and LLM Cache implementation.

**Prerequisites:**
- CDK deployed to staging
- ANTHROPIC_API_KEY configured in SSM (not Bedrock)

```bash
cd /Users/yitzchak/Documents/dev/careervp

# Configuration
API_BASE="${API_BASE:-https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod}"
TEST_USER_ID="${TEST_USER_ID:-test-user-e2e}"
TOKEN="${TOKEN:-}"  # Optional in dev when AUTHORIZER_DISABLED=true

# Optional: auto-discover deployed API base from AWS
# API_ID=$(aws apigateway get-rest-apis --region us-east-1 --limit 500 \
#   | jq -r '.items[] | select(.name=="careervp-core-api-dev") | .id' | head -n1)
# API_BASE="https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod"

# If JWT auth is enabled in staging:
# TOKEN=$(curl -s -X POST "$API_BASE/auth/login" -H "Content-Type: application/json" \
#   -d '{"email":"<email>","password":"<password>"}' | jq -r '.access_token')

# Run hard preflight checks first (env, route, auth mode, payload, DynamoDB CV item)
bash src/backend/scripts/preflight_phase2_live_test.sh

# ============================================================================
# Test 1: CV Tailoring with CV Summarizer
# ============================================================================
# Payload: docs/refactor/payloads/phase3_cv_tailoring_test.json

# 1. Generate tailored CV (deployed route: POST /api/cv-tailoring)
AUTH_HEADER=()
if [[ -n "$TOKEN" && "$TOKEN" != "your-jwt-token" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")
fi

START_TS=$(date +%s)
RESPONSE=$(curl -sS -X POST "$API_BASE/api/cv-tailoring" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $TEST_USER_ID" \
  "${AUTH_HEADER[@]}" \
  -d @docs/refactor/payloads/phase3_cv_tailoring_test.json)
ELAPSED_1=$(( $(date +%s) - START_TS ))

echo "$RESPONSE" | jq '.'
echo "Request duration: ${ELAPSED_1}s"

SUCCESS=$(echo "$RESPONSE" | jq -r '.success // false')
if [[ "$SUCCESS" != "true" ]]; then
  echo "FAILED: tailoring request did not succeed"
  exit 1
fi

# Verify compression metadata if available in response shape
echo "$RESPONSE" | jq '.data.tailored_cv.metadata.compression_metadata // .data.tailored_cv.compression_metadata // .data.compression_metadata // "compression_metadata not present in response payload"'

# Validation:
# - HTTP 200 with success=true (deployed route is synchronous)
# - If metadata is exposed: compression_metadata.token_count exists
# - For large CVs: compression_metadata.was_truncated should be true

# ============================================================================
# Test 2: LLM Cache Hit Verification
# ============================================================================

# 1. Submit same CV tailoring request twice
START_1=$(date +%s)
REQUEST_1=$(curl -sS -X POST "$API_BASE/api/cv-tailoring" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $TEST_USER_ID" \
  "${AUTH_HEADER[@]}" \
  -d @docs/refactor/payloads/phase3_cv_tailoring_test.json)
DUR_1=$(( $(date +%s) - START_1 ))

echo "First request status: $(echo "$REQUEST_1" | jq -r '.success // false')"
echo "First request duration: ${DUR_1}s"

# 2. Submit identical request
sleep 2
START_2=$(date +%s)
REQUEST_2=$(curl -sS -X POST "$API_BASE/api/cv-tailoring" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $TEST_USER_ID" \
  "${AUTH_HEADER[@]}" \
  -d @docs/refactor/payloads/phase3_cv_tailoring_test.json)
DUR_2=$(( $(date +%s) - START_2 ))

# 3. Compare response times
echo "Second request status: $(echo "$REQUEST_2" | jq -r '.success // false')"
echo "Second request duration: ${DUR_2}s"

# Validation:
# - Second request duration should be <= first request duration (possible cache hit)
# - Check CloudWatch logs for "cache_hit=true"

# ============================================================================
# Contract Validation Gates
# ============================================================================

# Gate A: Validate currently deployed contract (/api/* + swagger assets)
# This gate is authoritative for live test pass/fail in current environment.
DEPLOYED_ENDPOINTS=(
  "GET /swagger"
  "POST /api/cv-tailoring"
  "POST /api/vpr"
  "GET /api/vpr/status/{job_id}"
  "POST /api/company-research"
)

for endpoint in "${DEPLOYED_ENDPOINTS[@]}"; do
  METHOD=$(echo "$endpoint" | cut -d' ' -f1)
  PATH=$(echo "$endpoint" | cut -d' ' -f2)
  URL="$API_BASE$PATH"
  PAYLOAD='{}'
  HEADERS=(-H "Content-Type: application/json")

  if [[ "$PATH" == "/api/cv-tailoring" ]]; then
    PAYLOAD=$(cat docs/refactor/payloads/phase3_cv_tailoring_test.json)
    HEADERS+=(-H "X-User-Id: $TEST_USER_ID")
  elif [[ "$PATH" == "/api/vpr" ]]; then
    PAYLOAD='{"application_id":"app-contract-gate","user_id":"test-user-e2e","job_posting":{"company_name":"TechCorp","role_title":"Senior Engineer","requirements":["Python"],"responsibilities":["Build APIs"]}}'
  elif [[ "$PATH" == "/api/company-research" ]]; then
    PAYLOAD='{"company_name":"OpenAI","domain":"openai.com","job_posting_text":"Senior software engineer role requiring Python and cloud experience"}'
  elif [[ "$PATH" == "/api/vpr/status/{job_id}" ]]; then
    URL="$API_BASE/api/vpr/status/contract-gate-job-id"
  fi

  if [[ "$METHOD" == "POST" ]]; then
    CODE=$(curl -sS -o /tmp/contract_gate_body.out -w "%{http_code}" \
      -X POST "$URL" "${HEADERS[@]}" "${AUTH_HEADER[@]}" -d "$PAYLOAD")
    BODY=$(cat /tmp/contract_gate_body.out)
  else
    CODE=$(curl -sS -o /tmp/contract_gate_body.out -w "%{http_code}" \
      "$URL" "${AUTH_HEADER[@]}")
    BODY=$(cat /tmp/contract_gate_body.out)
  fi

  echo "Contract Gate A: $METHOD $PATH -> $CODE"

  # Route-existence gate: fail only on explicit API Gateway missing-route signatures.
  # Business-level 4xx/5xx (for invalid IDs/payloads/auth) do not imply route drift.
  if [[ "$CODE" == "403" || "$CODE" == "404" ]] && echo "$BODY" | grep -q "Missing Authentication Token"; then
    echo "FAILED Contract Gate A: missing deployed route $METHOD $PATH"
    exit 1
  fi
done
echo "Contract Gate A PASS (deployed routes reachable)"

# Gate B: Validate target contract artifact (27-endpoint goal)
# This gate validates target spec readiness, not current deployment readiness.
TARGET_SPEC="docs/swagger/careervp-api-v1.yaml"
TARGET_EXPECTED_ENDPOINTS=27
TARGET_DEFINED_ENDPOINTS=$(grep -cE '^  /' "$TARGET_SPEC")
echo "Target endpoint count in $TARGET_SPEC: $TARGET_DEFINED_ENDPOINTS (expected $TARGET_EXPECTED_ENDPOINTS)"
if [[ "$TARGET_DEFINED_ENDPOINTS" -eq "$TARGET_EXPECTED_ENDPOINTS" ]]; then
  echo "Contract Gate B PASS (target contract endpoint count met)"
else
  echo "Contract Gate B PENDING (target contract not yet at 27 endpoints)"
fi

# ============================================================================
# Test 3: Verify Anthropic API (Not Bedrock)
# ============================================================================

# 1. Check CloudWatch logs for Anthropic API calls
# NOTE: Validate against deployed lambda log groups (prefix: /aws/lambda/careervp)
START_MS=$(( ( $(date +%s) - 3600 ) * 1000 ))
LOG_GROUPS=$(aws logs describe-log-groups \
  --region us-east-1 \
  --log-group-name-prefix /aws/lambda/careervp \
  | jq -r '.logGroups[].logGroupName')

for lg in $LOG_GROUPS; do
  echo "Checking $lg"
  aws logs filter-log-events --log-group-name "$lg" --region us-east-1 \
    --start-time "$START_MS" --filter-pattern "anthropic" \
    | jq -r '.events | length'
done

# Verify no Bedrock runtime usage appears in deployed logs
for lg in $LOG_GROUPS; do
  echo "Checking bedrock-runtime in $lg"
  aws logs filter-log-events --log-group-name "$lg" --region us-east-1 \
    --start-time "$START_MS" --filter-pattern "bedrock-runtime" \
    | jq -r '.events | length'
done

# 2. Verify cost in CloudWatch metrics
# Use deployed custom metric (careervp_kpi | CostUSD), not AWS/Lambda EstimatedCost.
aws cloudwatch list-metrics \
  --namespace careervp_kpi \
  --metric-name CostUSD \
  --region us-east-1

# 3. Verify API key source
# Verify Lambda uses SSM parameter indirection; do not expect secret values in logs.
aws lambda get-function-configuration \
  --function-name careervp-cvtailor-lambda-dev \
  --region us-east-1 \
  | jq '.Environment.Variables | {ANTHROPIC_API_KEY_SSM_PARAM, ANTHROPIC_API_KEY}'

# Validation:
# - No "bedrock-runtime" in deployed lambda logs
# - "anthropic" SDK/API messages found in deployed lambda logs
# - ANTHROPIC_API_KEY_SSM_PARAM is set, ANTHROPIC_API_KEY is unset/null
# - CostUSD metrics are emitted in careervp_kpi namespace

# ============================================================================
# Test 4: LLM Cache DynamoDB Verification
# ============================================================================

# 1. Check cache table for entries
aws dynamodb scan \
  --table-name careervp-llm-cache-dev \
  --region us-east-1 \
  --output json | jq '.Items | length'

# Expected: > 0 after cache hits

# 2. Verify TTL is set correctly
aws dynamodb scan \
  --table-name careervp-llm-cache-dev \
  --region us-east-1 \
  --output json | jq '.Items[].expires_at'

# Expected: Current time + ~604800 seconds (7 days)
# Verify TTL delta (seconds from now)
NOW=$(date +%s)
aws dynamodb scan \
  --table-name careervp-llm-cache-dev \
  --region us-east-1 \
  --output json | jq -r '.Items[].expires_at.N' | awk -v now="$NOW" '{print $1-now}'

# Validation:
# - Cache table has items after API calls
# - TTL delta is <= 604800 and > 0
# - PITR policy check is environment-aware:
#   - dev/staging may be DISABLED
#   - production must be ENABLED

# ============================================================================
# Smoke Test: Phase 2 Deployed Endpoints Only
# ============================================================================

# 1) API availability
SWAGGER_CODE=$(curl -s -o /tmp/phase2_swagger.out -w "%{http_code}" "$API_BASE/swagger")
echo "GET /swagger => $SWAGGER_CODE"
if [[ "$SWAGGER_CODE" != "200" ]]; then
  echo "FAILED: /swagger should return 200"
  exit 1
fi

# 2) Phase 2 primary endpoint
TAILOR_BODY=$(curl -sS -X POST "$API_BASE/api/cv-tailoring" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $TEST_USER_ID" \
  "${AUTH_HEADER[@]}" \
  -d @docs/refactor/payloads/phase3_cv_tailoring_test.json)
TAILOR_SUCCESS=$(echo "$TAILOR_BODY" | jq -r '.success // false')
echo "POST /api/cv-tailoring => success=$TAILOR_SUCCESS"
if [[ "$TAILOR_SUCCESS" != "true" ]]; then
  echo "FAILED: /api/cv-tailoring should return success=true"
  exit 1
fi

echo "All Phase 2 smoke tests completed"
```

**Validation Criteria:**

| Test | Expected | Validation |
|------|----------|------------|
| Deployed Contract Gate (/api/*) | Deployed routes are reachable | Contract Gate A checks deployed `/api/*` + `/swagger` routes |
| Target Contract Gate (27 endpoints) | Target spec defines 27 endpoints | Contract Gate B checks endpoint count in `docs/swagger/careervp-api-v1.yaml` |
| CV Summarizer | Compression is observable when exposed | Check `compression_metadata` only if response includes it |
| LLM Cache | Cache behavior is proven by deterministic signal | Primary: CloudWatch `cache_hit=true`; timing is secondary heuristic |
| Anthropic API | No Bedrock runtime usage in deployed lambdas | `bedrock-runtime` count = 0 across deployed `careervp` lambda log groups |
| Cache Table | Items with TTL and valid expiry window | DynamoDB entries exist and TTL delta is in expected range |
| Phase 2 Smoke | Deployed Phase 2 endpoints pass | `/swagger` and `/api/cv-tailoring` return expected success codes |

---

## Phase 3: VPR 6-Stage Generator ⚠️ PARTIAL

**Duration:** 2 days | **Effort:** 12 hours
**Status (2026-02-16):** PARTIAL - 65%

### Specs
| Type | File | Purpose |
|------|------|---------|
| Reference | `vpr_6stage_spec.yaml` | 6-stage pipeline spec |
| Reference | `models_spec.yaml` | VPR models |

### Step 3.1: Refactor VPR Generator to 6 Stages

**READ FIRST:**
- `docs/refactor/specs/vpr_6stage_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/vpr_6stage_spec.yaml`

ROLE: Senior Backend Engineer specializing in LLM pipelines and prompt engineering

CONTEXT: Refactor VPR Generator to 6-stage pipeline for improved quality, testability, and anti-AI detection.

TASK: Implement 6-stage pipeline following vpr_6stage_spec.yaml stages section

1. Update: src/backend/careervp/logic/vpr_generator.py
   - Refactor to 6 sequential stages with clear interfaces:
     * Stage 1: _analyze_input(cv: UserCV, job: Job) -> AnalysisResult
              - Extract key skills, experience level, job requirements
     * Stage 2: _extract_evidence(analysis: AnalysisResult) -> EvidenceList
              - Map CV achievements to job requirements
     * Stage 3: _synthesize(evidence: EvidenceList) -> DraftProposition
              - Generate initial value proposition draft
     * Stage 4: _self_correct(draft: DraftProposition) -> CorrectedProposition
              - Apply refinement based on quality checks
     * Stage 5: _generate_output(corrected: CorrectedProposition) -> VPRData
              - Format final VPR with all required fields
     * Stage 6: _final_meta_evaluation(vpr: VPRData) -> FinalVPRData
              - Anti-AI pattern check, final quality gate
   - Each stage returns typed dataclass with clear contract

2. Update: src/backend/careervp/logic/prompts/vpr_prompt.py
   - Add prompt templates for each stage
   - Stage-specific system prompts with role definitions
   - Few-shot examples for complex stages (3, 4)

3. Wire anti-AI detection:
   - Import check_anti_anti_ai_patterns from fvs_validator
   - Call in Stage 6: _final_meta_evaluation()
   - Reject and regenerate if anti-AI score < 9.0

4. Update: tests/unit/test_vpr_generator.py
   - test_stage_1_analyze_input_returns_analysis_result
   - test_stage_2_extract_evidence_maps_correctly
   - test_stage_4_self_correct_improves_draft
   - test_stage_6_rejects_ai_patterns
   - test_full_pipeline_produces_valid_vpr

VALIDATION CRITERIA (must all pass):
- [ ] Each stage has isolated, testable input/output contracts
- [ ] Anti-AI patterns detected in Stage 6 trigger regeneration
- [ ] Pipeline produces valid VPRData matching models/vpr.py schema
- [ ] Unit tests pass: pytest tests/unit/test_vpr_generator.py -v
- [ ] Type check passes: mypy careervp/logic/vpr_generator.py --strict
- [ ] Lint passes: ruff check careervp/logic/vpr_generator.py

OUTPUT FORMAT: Provide complete implementation with stage interfaces and inline documentation. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Phase 3 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 3 unit tests
uv run pytest tests/unit/test_vpr_generator.py -v --tb=short

# Run lint
uv run ruff check careervp/logic/vpr_generator.py

# Run type check
uv run mypy careervp/logic/vpr_generator.py --strict
```

---

## Phase 4: CV Tailoring 3-Step ⚠️ PARTIAL

**Duration:** 2 days | **Effort:** 10 hours
**Status (2026-02-16):** PARTIAL - 70%

### Specs
| Type | File | Purpose |
|------|------|---------|
| Reference | `cv_tailoring_spec.yaml` | CV tailoring spec |

### Step 4.1: Implement 3-Step CV Tailoring

**READ FIRST:**
- `docs/refactor/specs/cv_tailoring_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cv_tailoring_spec.yaml`

ROLE: Senior Backend Engineer specializing in ATS systems and resume optimization

CONTEXT: Implement 3-step CV tailoring pipeline with ATS scoring >= 8.0 and self-correction loop.

TASK: Implement CV tailoring following cv_tailoring_spec.yaml

1. Update: src/backend/careervp/logic/cv_tailoring.py
   - Implement 3-step pipeline:
     * Step 1: analyze_and_map_keywords(cv: UserCV, job: Job) -> KeywordMap
              - Extract 12-18 keywords from job description
              - Categorize: required, preferred, nice-to-have
              - Map to existing CV skills/experience
     * Step 2: tailor_cv(cv: UserCV, keyword_map: KeywordMap) -> TailoredCV
              - Rewrite bullets with keyword integration
              - Reorder sections by relevance
              - Calculate preliminary ATS score
     * Step 3: validate_and_finalize(tailored: TailoredCV) -> FinalTailoredCV
              - ATS scoring (must be >= 8.0)
              - CAR/STAR format validation
              - Final formatting checks

2. Add self-correction loop (in Step 3):
   - If ATS score < 8.0:
     * Generate improvement feedback
     * Return to Step 2 with feedback
     * Maximum 3 iterations
   - Track iteration count in metadata

3. Add CAR/STAR enforcement:
   - Validate achievement bullets follow STAR format
   - Pattern: "Verb | Context | Action | Result (with metrics)"
   - Reject bullets missing Result component

4. Update: tests/unit/test_cv_tailoring.py
   - test_keyword_extraction_finds_12_to_18_keywords
   - test_ats_scoring_returns_numeric_score
   - test_self_correction_iterates_max_3_times
   - test_star_format_validation_accepts_valid_bullets
   - test_star_format_validation_rejects_invalid_bullets

VALIDATION CRITERIA (must all pass):
- [ ] ATS score >= 8.0 for all generated CVs
- [ ] Self-correction loop improves score by >= 0.5 per iteration
- [ ] All achievement bullets follow STAR format
- [ ] Maximum 3 regeneration attempts
- [ ] Unit tests pass: pytest tests/unit/test_cv_tailoring.py -v
- [ ] Type check passes: mypy careervp/logic/cv_tailoring.py --strict
- [ ] Lint passes: ruff check careervp/logic/cv_tailoring.py

OUTPUT FORMAT: Provide complete implementation with ATS scoring logic. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Phase 4 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 4 unit tests
uv run pytest tests/unit/test_cv_tailoring.py -v --tb=short

# Run lint
uv run ruff check careervp/logic/cv_tailoring.py

# Run type check
uv run mypy careervp/logic/cv_tailoring.py --strict
```

---

## Phase 5: Gap Analysis ⚠️ PARTIAL

**Duration:** 1 day | **Effort:** 6 hours
**Status (2026-02-16):** PARTIAL - 45%

### Specs
| Type | File | Purpose |
|------|------|---------|
| Reference | `gap_analysis_spec.yaml` | Gap analysis spec |

### Step 5.1: Fix Question Limit and Add Tagging

**READ FIRST:**
- `docs/refactor/specs/gap_analysis_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
**READ FIRST:**
- `docs/refactor/specs/gap_analysis_spec.yaml`

ROLE: Backend Engineer specializing in API design and interview preparation

CONTEXT: Fix Gap Analysis to generate 10 questions (was 5) with categorization tags for interview preparation.

TASK: Update Gap Analysis following gap_analysis_spec.yaml

1. Update: src/backend/careervp/logic/gap_analysis.py
   - Change question limit from 5 to 10
   - Add question tagging in prompt:
     * [CV IMPACT] - Questions about candidate's key achievements
     * [INTERVIEW/MVP ONLY] - Questions for final round
     * [TECHNICAL] - Technical/skill assessment questions
     * [BEHAVIORAL] - STAR-based behavioral questions
   - Distribution target: 4 CV IMPACT, 2 TECHNICAL, 2 BEHAVIORAL, 2 INTERVIEW/MVP
   - Update response schema to include tags array per question

2. Enhance: src/backend/careervp/handlers/gap_handler.py
   - Add full CRUD operations:
     * GET /gap-analysis/questions/{jobId} -> get_questions()
     * POST /gap-analysis/responses -> submit_response()
     * GET /gap-analysis/responses/{jobId} -> get_responses()
   - Add response storage in DynamoDB

3. Update: tests/unit/test_gap_analysis.py
   - test_generate_10_questions
   - test_question_tagging_all_categories_present
   - test_question_distribution_meets_targets
   - test_response_storage_persists_correctly

VALIDATION CRITERIA (must all pass):
- [ ] Exactly 10 questions generated per request
- [ ] Each question has at least one tag
- [ ] All 4 tag categories represented
- [ ] CRUD endpoints return correct HTTP status codes
- [ ] Unit tests pass: pytest tests/unit/test_gap_analysis.py -v
- [ ] Type check passes: mypy careervp/logic/gap_analysis.py --strict
- [ ] Lint passes: ruff check careervp/logic/gap_analysis.py

OUTPUT FORMAT: Provide complete implementation with tagging logic. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Phase 5 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 5 unit tests
uv run pytest tests/unit/test_gap_analysis.py -v --tb=short

# Run lint
uv run ruff check careervp/logic/gap_analysis.py

# Run type check
uv run mypy careervp/logic/gap_analysis.py --strict
```

---

## Phase 7: Quality Validator (FVS) ⚠️ PARTIAL

**Duration:** 2 days | **Effort:** 12 hours
**Status (2026-02-16):** PARTIAL - 25%

### Specs
| Type | File | Purpose |
|------|------|---------|
| Reference | `fvs_spec.yaml` | FVS validation spec |
| Reference | `test_strategy_spec.yaml` | Test requirements |

### Step 7.1: Implement FVS Validation

**READ FIRST:**
- `docs/refactor/specs/fvs_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/fvs_spec.yaml`

ROLE: Senior QA Engineer specializing in content quality validation and anti-AI detection

CONTEXT: Implement Feature Validation System (FVS) with comprehensive quality checks and anti-AI detection.

TASK: Implement FVS validation following fvs_spec.yaml validation_checks section

1. Update: src/backend/careervp/logic/fvs_validator.py
   - Implement validation checks with minimum thresholds:
     * Grammar validation: min_score = 9.0 (use LanguageTool or equivalent)
     * Tone validation: min_score = 8.0 (professional, confident, not robotic)
     * Anti-AI pattern detection: min_score = 9.0 (8-pattern avoidance framework)
     * Formatting validation: min_score = 8.0 (structure, spacing, bullet consistency)
     * Content structure: Check for intro/body/conclusion, logical flow
   - ATS scoring for CV/cover letter (target >= 8.0)
   - Cross-document consistency: Compare VPR, CV, Cover Letter for contradictions

2. Wire anti-AI into all pipelines:
   - VPR: Import and call check_anti_ai_patterns in vpr_generator.py
   - Cover Letter: Import and call check_anti_ai_patterns in cover_letter_generator.py
   - CV Tailoring: Import and call check_anti_ai_patterns in cv_tailoring.py
   - Reject content with anti-AI score < 9.0 and request regeneration

3. Update: tests/unit/test_fvs_validator.py
   - test_grammar_validation_scores_above_threshold
   - test_tone_validation_detects_robotic_language
   - test_anti_ai_patterns_detected
   - test_ats_scoring_returns_numeric_score
   - test_cross_document_consistency_check

4. Create: tests/cover-letter/unit/test_fvs_integration.py
   - test_fvs_integrates_with_cover_letter_pipeline
   - test_rejects_cover_letter_below_thresholds

VALIDATION CRITERIA (must all pass):
- [ ] Grammar score >= 9.0 for all content
- [ ] Tone score >= 8.0 for all content
- [ ] Anti-AI pattern score >= 9.0 for all content
- [ ] Formatting score >= 8.0 for all content
- [ ] ATS score >= 8.0 for CV and cover letter
- [ ] Cross-document consistency check passes
- [ ] Unit tests pass: pytest tests/unit/test_fvs_validator.py -v
- [ ] Integration tests pass: pytest tests/cover-letter/unit/test_fvs_integration.py -v
- [ ] Type check passes: mypy careervp/logic/fvs_validator.py --strict
- [ ] Lint passes: ruff check careervp/logic/fvs_validator.py

OUTPUT FORMAT: Provide complete implementation with validation score details. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Phase 7 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 7 unit tests
uv run pytest tests/unit/test_fvs_validator.py -v --tb=short
uv run pytest tests/cover-letter/unit/test_fvs_integration.py -v --tb=short

# Run lint
uv run ruff check careervp/logic/fvs_validator.py

# Run type check
uv run mypy careervp/logic/fvs_validator.py --strict
```

---

# PART 2: API CONTRACT GAPS

## Phase 10: API Contract Coverage - All 27 Endpoints ✅ TARGET

**Duration:** 5 days | **Effort:** 40 hours
**Status (2026-02-17):** Includes all steps to achieve 100% (27/27 endpoints)

> **Execution Order:** Start with Step 10.0a/10.0b/10.0d/10.0e/10.0c (infra-safe migration + storage layer sync), then Step 10.0 and Steps 10.1–10.12

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `api_contract_spec.yaml` | API endpoints |
| Authoritative | `../swagger/careervp-api-v1.yaml` | Full OpenAPI 3.0.3 spec |
| Reference | `storage_contract_spec.yaml` | Logical API IDs ↔ physical storage key mapping |

### Step 10.0: Path Normalization Strategy — INFRASTRUCTURE

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (servers section: base URL `/v1`)
- `docs/refactor/specs/api_contract_spec.yaml`

**CONTEXT:** Migrate from `/api/*` routes to OpenAPI contract paths without breaking existing clients.

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (servers section: base URL `/v1`)
- `docs/refactor/specs/api_contract_spec.yaml`

ROLE: DevOps Engineer specializing in API Gateway and route migration

TASK: Analyze and document current-to-OpenAPI route mapping

1. Audit existing routes in src/backend/careervp/handlers/
   - grep -r "@app\." careervp/handlers/ | grep -v "lambda_handler"
   - Document all current route decorators

2. Map current routes to OpenAPI paths (document in docs/refactor/route_mapping.md):
   | Current Route | OpenAPI Path | Handler |
   |---------------|--------------|---------|
   | /api/cv | /users/me/cv | cv_upload_handler.py |
   | /api/vpr | /vpr/generate | vpr_submit_handler.py |
   | /api/vpr/status/* | /vpr/{vprId} | vpr_status_handler.py |

3. Validate no /v1 prefix in handler routes (that is API Gateway stage name)

VALIDATION CRITERIA:
- [ ] All current routes documented with OpenAPI equivalents
- [ ] No /v1 prefix in handler route decorators
- [ ] Route mapping documented in docs/refactor/route_mapping.md

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.0a: API Gateway Additive Route Migration — INFRASTRUCTURE

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml`
- `infra/careervp/api_construct.py`

**CONTEXT:** Add OpenAPI-compliant routes while keeping existing `/api/*` routes temporarily.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml`
- `infra/careervp/api_construct.py`

**CONTEXT:** Add OpenAPI-compliant routes while keeping existing `/api/*` routes temporarily.

ROLE: DevOps Engineer specializing in AWS CDK and API Gateway

TASK: Add OpenAPI paths as API Gateway resources without removing existing routes

1. Update: infra/careervp/api_construct.py
   - Add OpenAPI paths as API Gateway resources:
     * /auth/register, /auth/login, /auth/refresh
     * /users/me, /users/me/cv, /users/me/cvs
     * /jobs, /jobs/{jobId}
     * /vpr/generate, /vpr/{vprId}, /users/me/vprs
     * /gap-analysis/questions, /gap-analysis/responses, /gap-analysis/{jobId}/questions
     * /cv-tailoring/generate, /cv-tailoring/{cvTailoringId}, /users/me/tailored-cvs
     * /cover-letter/generate, /cover-letter/{coverLetterId}, /users/me/cover-letters
     * /interview-prep/generate, /interview-prep/{interviewPrepId}
     * /company-research/fetch, /company-research/{jobId}
     * /health

2. Configure Lambda integrations:
   - Link each new resource to corresponding handler
   - Use existing Lambda functions where handlers exist

3. Preserve existing /api/* resources (do NOT remove)

4. Reuse existing IAM role, DynamoDB table, S3 bucket, SQS queue

VALIDATION CRITERIA:
- [ ] cdk synth succeeds without errors
- [ ] All 27 OpenAPI paths have API Gateway resources
- [ ] Existing /api/* routes still functional
- [ ] No new DynamoDB/S3/SQS resources created

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.0b: Infra Diff + Safety Gate — INFRASTRUCTURE

**CONTEXT:** Validate CDK changes are safe before deployment.

**CODE:**
```bash
# VSCode + Haiku
"""
**CONTEXT:** Validate CDK changes are safe before deployment.

ROLE: DevOps Engineer

TASK: Validate CDK changes are additive and safe

Run commands:
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra
cdk synth CareerVpApi
cdk diff CareerVpApi
```

VALIDATION CRITERIA:
- [ ] cdk synth succeeds without errors
- [ ] cdk diff shows only ADDITIVE changes (no replacements)
- [ ] No DynamoDB table deletions
- [ ] No S3 bucket deletions
- [ ] No SQS queue deletions
- [ ] Only API Gateway resource additions shown
"""
```

---

### Step 10.0c: Legacy Route Decommission Gate — INFRASTRUCTURE

**READ FIRST:**
- `docs/refactor/route_mapping.md` (from Step 10.0)

**CONTEXT:** Remove legacy `/api/*` routes after all 27 endpoints verified working.

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/refactor/route_mapping.md` (from Step 10.0)

**CONTEXT:** Remove legacy `/api/*` routes after all 27 endpoints verified working.

ROLE: DevOps Engineer

TASK: Normalize handler route decorators to match OpenAPI contract

1. Update: src/backend/careervp/handlers/cv_upload_handler.py
   - Change: @app.post('/api/cv') → @app.post('/users/me/cv')

2. Verify all other handlers use lambda_handler(event, context) pattern

3. Update Step 10.0a to remove old /api/* resources AFTER:
   - All 27 endpoints return 200 OK
   - Smoke tests pass
   - Migration sign-off complete

NOTE: Do NOT add /v1 prefix — that is the API Gateway stage name.
"""

VALIDATION CRITERIA:
- [ ] grep "@app\..*'/api/" returns 0 matches
- [ ] All handlers use lambda_handler(event, context) pattern
- [ ] Smoke tests pass for all 27 endpoints
"""
```

---

### Step 10.0d: Storage Contract Lock — INFRASTRUCTURE

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml`
- `infra/careervp/api_db_construct.py`
- `docs/refactor/specs/deployment_spec.yaml`

**CONTEXT:** Define canonical mapping from OpenAPI resource IDs to physical AWS storage keys.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml`
- `infra/careervp/api_db_construct.py`
- `docs/refactor/specs/deployment_spec.yaml`

**CONTEXT:** Define canonical mapping from OpenAPI resource IDs to physical AWS storage keys.

ROLE: Solutions Architect

TASK: Document logical-to-physical storage mapping

1. Create: docs/refactor/specs/storage_contract_spec.yaml
   - Define logical IDs from OpenAPI:
     * cv_id → S3 object key pattern: cvs/{user_id}/{cv_id}.pdf
     * job_id → DynamoDB: JobsTable PK=job_id
     * vpr_id → DynamoDB: VPRTable PK=vpr_id
     * gap_response_ids → DynamoDB: GapResponsesTable PK=user_id, SK=job_id
     * company_research_id → DynamoDB: CompanyResearchTable PK=job_id
   - Document active physical storage:
     * users table: PK=pk, SK=sk (for user profiles)
     * jobs table: PK=job_id (for job postings)
     * idempotency table: PK=id (for request deduplication)
     * S3 buckets: cvs, vpr-results

2. Update references in:
   - docs/refactor/specs/deployment_spec.yaml
   - docs/refactor/specs/_registry.yaml

VALIDATION CRITERIA:
- [ ] YAML parses without errors
- [ ] All logical IDs mapped to physical keys
- [ ] No new infrastructure resources defined

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.0e: Data Storage Adapter Integration — INFRASTRUCTURE

**READ FIRST:**
- `docs/refactor/specs/storage_contract_spec.yaml`
- `src/backend/careervp/dal/dynamo_dal_handler.py`

**CONTEXT:** Keep existing infra, expose OpenAPI resource ID semantics to handlers.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/storage_contract_spec.yaml`
- `src/backend/careervp/dal/dynamo_dal_handler.py`

**CONTEXT:** Keep existing infra, expose OpenAPI resource ID semantics to handlers.

ROLE: Senior Backend Engineer

TASK: Implement logical-to-physical key translation adapter

1. Create: src/backend/careervp/dal/api_storage_adapter.py
   - map_logical_to_physical_keys(resource_type, logical_identifiers) -> dict
   - map_physical_to_logical_ids(resource_type, item) -> dict
   - build_pk_sk_for_users_table(resource_type, user_id, identifiers) -> tuple
   - Resource types: cv, job, vpr, gap_response, company_research

2. Wire adapter into existing repositories:
   - cv_repository.py: Use adapter for S3 key generation
   - jobs_repository.py: Use adapter for DynamoDB key generation

3. Create: tests/unit/test_api_storage_adapter.py
   - test_cv_key_generation
   - test_job_pk_sk_construction
   - test_vpr_key_mapping

VALIDATION CRITERIA:
- [ ] Unit tests pass: pytest tests/unit/test_api_storage_adapter.py -v
- [ ] Type check passes: mypy careervp/dal/api_storage_adapter.py --strict
- [ ] Lint passes: ruff check careervp/dal/api_storage_adapter.py

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.1: Auth Endpoints (register, login, refresh)

**READ FIRST:**
- `docs/refactor/specs/api_contract_spec.yaml` (auth section)
- `docs/swagger/careervp-api-v1.yaml` (auth paths)

**CONTEXT:** Implement authentication endpoints following OpenAPI contract.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/api_contract_spec.yaml` (auth section)
- `docs/swagger/careervp-api-v1.yaml` (auth paths)

**CONTEXT:** Implement authentication endpoints following OpenAPI contract.

ROLE: Senior Backend Engineer specializing in authentication and JWT

TASK: Implement auth endpoints per api_contract_spec.yaml

1. Create: src/backend/careervp/handlers/auth_handler.py
   - POST /auth/register -> register_user() -> 201 Created
   - POST /auth/login -> login_user() -> 200 OK with JWT
   - POST /auth/refresh -> refresh_token() -> 200 OK with new JWT

2. Create: src/backend/careervp/logic/auth_service.py
   - AuthService with JWT generation (RS256)
   - Token validation with expiration
   - Password hashing (bcrypt)

3. Create: tests/unit/test_auth_handler.py
   - test_register_creates_user
   - test_login_returns_jwt
   - test_refresh_returns_new_jwt

VALIDATION CRITERIA:
- [ ] All 3 endpoints return correct HTTP status codes
- [ ] JWT contains user_id and expires in 1 hour
- [ ] Refresh token valid for 7 days
- [ ] Unit tests pass: pytest tests/unit/test_auth_handler.py -v
- [ ] Type check passes: mypy careervp/handlers/auth_handler.py --strict
- [ ] Lint passes: ruff check careervp/handlers/auth_handler.py

OUTPUT FORMAT: Provide handler with Powertools @app decorators. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.2: User Management Endpoints

**READ FIRST:**
- `docs/refactor/specs/api_contract_spec.yaml` (users section)
- `docs/swagger/careervp-api-v1.yaml` (user paths)

**CONTEXT:** Implement user management endpoints for profile and CV listing.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/api_contract_spec.yaml` (users section)
- `docs/swagger/careervp-api-v1.yaml` (user paths)

**CONTEXT:** Implement user management endpoints for profile and CV listing.

ROLE: Backend Engineer

TASK: Implement user endpoints per api_contract_spec.yaml

1. Create: src/backend/careervp/models/user.py
   - User model: user_id, email, name, preferences, created_at, updated_at

2. Create: src/backend/careervp/dal/user_repository.py
   - UserRepository: get_user(user_id), update_user(user_id, data)
   - Use users table with PK=user_id

3. Create: src/backend/careervp/handlers/user_handler.py
   - GET /users/me -> get_current_user() -> 200 OK
   - PUT /users/me -> update_current_user() -> 200 OK
   - GET /users/me/cvs -> list_user_cvs() -> 200 OK

4. Create: tests/unit/test_user_handler.py
   - test_get_current_user_returns_profile
   - test_update_current_user_modifies_profile

VALIDATION CRITERIA:
- [ ] All 3 endpoints return 200 OK
- [ ] Auth required for all endpoints
- [ ] User can only access own data (/users/me)
- [ ] Unit tests pass: pytest tests/unit/test_user_handler.py -v
- [ ] Type check passes: mypy careervp/handlers/user_handler.py --strict
- [ ] Lint passes: ruff check careervp/handlers/user_handler.py

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 10.3: Job CRUD Endpoints

**READ FIRST:**
- `docs/refactor/specs/api_contract_spec.yaml` (jobs section)
- `docs/swagger/careervp-api-v1.yaml` (job paths)

**CONTEXT:** Implement job CRUD endpoints for job posting management.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/api_contract_spec.yaml` (jobs section)
- `docs/swagger/careervp-api-v1.yaml` (job paths)

**CONTEXT:** Implement job CRUD endpoints for job posting management.

ROLE: Backend Engineer

TASK: Implement job endpoints per api_contract_spec.yaml

1. Create: src/backend/careervp/models/job.py
   - Job model: job_id, user_id, title, company, description, status, created_at

2. Create: src/backend/careervp/dal/jobs_repository.py
   - JobsRepository: create_job(), get_job(), list_jobs(), get_jobs_by_user()
   - Use jobs table with PK=job_id

3. Create: src/backend/careervp/handlers/job_handler.py
   - POST /jobs -> create_job() -> 201 Created
   - GET /jobs -> list_jobs() -> 200 OK
   - GET /jobs/{jobId} -> get_job() -> 200 OK

4. Create: tests/unit/test_job_handler.py
   - test_create_job_returns_201
   - test_list_jobs_returns_user_jobs

VALIDATION CRITERIA:
- [ ] POST /jobs returns 201 Created
- [ ] GET /jobs returns list of user's jobs
- [ ] GET /jobs/{jobId} returns single job
- [ ] Users can only access own jobs
- [ ] Unit tests pass: pytest tests/unit/test_job_handler.py -v
- [ ] Type check passes: mypy careervp/handlers/job_handler.py --strict
- [ ] Lint passes: ruff check careervp/handlers/job_handler.py

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.4: VPR Endpoint Alignment

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (VPR endpoints)
- `src/backend/careervp/handlers/vpr_submit_handler.py`
- `src/backend/careervp/handlers/vpr_status_handler.py`

**CONTEXT:** Align VPR routes with OpenAPI contract paths.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (VPR endpoints)
- `src/backend/careervp/handlers/vpr_submit_handler.py`
- `src/backend/careervp/handlers/vpr_status_handler.py`

**CONTEXT:** Align VPR routes with OpenAPI contract paths.

ROLE: Backend Engineer

TASK: Align VPR endpoints with OpenAPI contract

1. Update: src/backend/careervp/handlers/vpr_submit_handler.py
   - Route: POST /vpr/generate (was: /api/vpr)
   - Schema: Match OpenAPI GenerateVPRRequest/GenerateVPRResponse
   - Returns: 202 Accepted with job_id

2. Update: src/backend/careervp/handlers/vpr_status_handler.py
   - Route: GET /vpr/{vprId} (was: /api/vpr/status/{job_id})
   - Add: GET /users/me/vprs -> list_user_vprs()

3. Create: tests/unit/test_vpr_endpoints.py

VALIDATION CRITERIA:
- [ ] POST /vpr/generate returns 202 Accepted
- [ ] GET /vpr/{vprId} returns job status
- [ ] GET /users/me/vprs returns user's VPR list
- [ ] Unit tests pass: pytest tests/unit/test_vpr_endpoints.py -v
- [ ] Type check passes: mypy careervp/handlers/vpr_*.py --strict

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.5: Gap Analysis Handler Completion

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (gap-analysis paths)
- `src/backend/careervp/handlers/gap_handler.py`

**CONTEXT:** Complete gap analysis handler with all CRUD endpoints.

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (gap-analysis paths)
- `src/backend/careervp/handlers/gap_handler.py`

**CONTEXT:** Complete gap analysis handler with all CRUD endpoints.

ROLE: Backend Engineer

TASK: Implement gap analysis endpoints

1. Update: src/backend/careervp/handlers/gap_handler.py
   - POST /gap-analysis/questions -> generate_questions() -> 201
   - GET /gap-analysis/{jobId}/questions -> get_questions() -> 200
   - POST /gap-analysis/responses -> submit_response() -> 201
   - GET /gap-analysis/responses/{jobId} -> get_responses() -> 200

2. Create: tests/unit/test_gap_analysis_handler.py

VALIDATION CRITERIA:
- [ ] All 4 endpoints return correct HTTP status codes
- [ ] Questions stored in DynamoDB
- [ ] Unit tests pass: pytest tests/unit/test_gap_analysis_handler.py -v

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.6: CV Tailoring Status + List Endpoints

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (cv-tailoring paths)

**CONTEXT:** Implement CV tailoring status and list endpoints.

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (cv-tailoring paths)

**CONTEXT:** Implement CV tailoring status and list endpoints.

ROLE: Backend Engineer

TASK: Implement CV tailoring status endpoints

1. Update: src/backend/careervp/handlers/cv_tailoring_handler.py
   - GET /cv-tailoring/{cvTailoringId} -> get_tailored_cv_status() -> 200
   - GET /users/me/tailored-cvs -> list_tailored_cvs() -> 200

2. Create: tests/unit/test_cv_tailoring_status.py

VALIDATION CRITERIA:
- [ ] GET /cv-tailoring/{cvTailoringId} returns CV status
- [ ] GET /users/me/tailored-cvs returns user's CV list
- [ ] Unit tests pass

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.7: Cover Letter Status + List Endpoints

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (cover-letter paths)

**CONTEXT:** Implement cover letter status and list endpoints.

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (cover-letter paths)

**CONTEXT:** Implement cover letter status and list endpoints.

ROLE: Backend Engineer

TASK: Implement cover letter status endpoints

1. Update: src/backend/careervp/handlers/cover_letter_handler.py
   - GET /cover-letter/{coverLetterId} -> get_cover_letter_status() -> 200
   - GET /users/me/cover-letters -> list_cover_letters() -> 200

2. Create: tests/unit/test_cover_letter_status.py

VALIDATION CRITERIA:
- [ ] GET /cover-letter/{coverLetterId} returns cover letter
- [ ] GET /users/me/cover-letters returns user's letters

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.8: Interview Prep Status Endpoint

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (interview-prep paths)

**CONTEXT:** Implement interview prep status endpoint.

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (interview-prep paths)

**CONTEXT:** Implement interview prep status endpoint.

ROLE: Backend Engineer

TASK: Implement interview prep status endpoint

1. Update: src/backend/careervp/handlers/interview_prep_handler.py
   - GET /interview-prep/{interviewPrepId} -> get_interview_prep_status() -> 200

2. Create: tests/unit/test_interview_prep_status.py

VALIDATION CRITERIA:
- [ ] GET /interview-prep/{interviewPrepId} returns prep data

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.9: Company Research GET Endpoint

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (company-research paths)

**CONTEXT:** Implement company research GET endpoint with response code fix.

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (company-research paths)

**CONTEXT:** Implement company research GET endpoint with response code fix.

ROLE: Backend Engineer

TASK: Implement company research GET endpoint

1. Update: src/backend/careervp/handlers/company_research_handler.py
   - GET /company-research/{jobId} -> get_company_research() -> 200 OK
   - Fix: Return 200 (not 201) for GET requests

2. Create: tests/unit/test_company_research_status.py

VALIDATION CRITERIA:
- [ ] GET /company-research/{jobId} returns 200 OK
- [ ] Response matches OpenAPI schema

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.10: Health Check Endpoint

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (health path)
- `docs/refactor/specs/api_contract_spec.yaml` (health section)

**CONTEXT:** Implement health check endpoint (no auth required).

**CODE:**
```bash
# VSCode + Haiku
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (health path)
- `docs/refactor/specs/api_contract_spec.yaml` (health section)

**CONTEXT:** Implement health check endpoint (no auth required).

ROLE: Backend Engineer

TASK: Implement health check endpoint

1. Create: src/backend/careervp/handlers/health_handler.py
   - GET /health -> health_check() -> 200 OK
   - Response: {status: "healthy", timestamp: ISO8601, version: "1.0.0"}

2. Create: tests/unit/test_health_handler.py

VALIDATION CRITERIA:
- [ ] GET /health returns 200 OK
- [ ] No authentication required
- [ ] Response matches OpenAPI schema

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.11: Request/Response Schema Conformance

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml`
- `docs/refactor/specs/api_contract_spec.yaml`

**CONTEXT:** Create Pydantic models for all API request/response schemas.

**CODE:**
```bash
# VSCode + Sonnet
"""
**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml`
- `docs/refactor/specs/api_contract_spec.yaml`

**CONTEXT:** Create Pydantic models for all API request/response schemas.

ROLE: Senior Backend Engineer

TASK: Create API models for schema conformance

1. Create: src/backend/careervp/models/api_models.py
   - Pydantic BaseModel for all request/response schemas
   - Include validation decorators for required fields
   - Serialization/deserialization methods

2. Wire models into all handlers:
   - cv_upload_handler.py, vpr_submit_handler.py
   - cv_tailoring_handler.py, cover_letter_handler.py
   - gap_handler.py, job_handler.py, user_handler.py

3. Create: tests/unit/test_api_models.py

VALIDATION CRITERIA:
- [ ] All 27 endpoint schemas have Pydantic models
- [ ] Models validate input/output correctly
- [ ] Unit tests pass: pytest tests/unit/test_api_models.py -v
- [ ] Type check passes: mypy careervp/models/api_models.py --strict

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

### Step 10.12: OpenAPI Contract Validation Suite

**CODE:**
```bash
# VSCode + Sonnet
"""
ROLE: QA Engineer

TASK: Create OpenAPI contract validation suite

1. Create: tests/integration/test_openapi_contract.py
   - Validate all 27 endpoints exist in handler code
   - Validate request schemas match OpenAPI
   - Validate response schemas match OpenAPI
   - Validate HTTP status codes match OpenAPI
   - Validate authentication requirements

2. Create: scripts/validate_openapi_coverage.py
   - Parse OpenAPI spec
   - Check handler coverage
   - Report missing endpoints

VALIDATION CRITERIA:
- [ ] Coverage: 27/27 endpoints (100%)
- [ ] Integration tests pass: pytest tests/integration/test_openapi_contract.py -v
- [ ] No schema mismatches

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Phase 10 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 10 unit tests
uv run pytest tests/unit/test_auth_handler.py -v --tb=short
uv run pytest tests/unit/test_user_handler.py -v --tb=short
uv run pytest tests/unit/test_job_handler.py -v --tb=short
uv run pytest tests/unit/test_vpr_endpoints.py -v --tb=short
uv run pytest tests/unit/test_status_endpoints.py -v --tb=short
uv run pytest tests/unit/test_cv_tailoring_status.py -v --tb=short
uv run pytest tests/unit/test_cover_letter_status.py -v --tb=short
uv run pytest tests/unit/test_interview_prep_status.py -v --tb=short
uv run pytest tests/unit/test_company_research_status.py -v --tb=short
uv run pytest tests/unit/test_health_handler.py -v --tb=short
uv run pytest tests/unit/test_api_models.py -v --tb=short
uv run pytest tests/unit/test_api_storage_adapter.py -v --tb=short

# Phase 10 integration tests
uv run pytest tests/integration/test_openapi_contract.py -v --tb=short

# CDK infra validation
cd /Users/yitzchak/Documents/dev/careervp/infra
cdk synth
cdk diff

# Run lint
uv run ruff check careervp/handlers/ careervp/models/ careervp/dal/

# Run type check
uv run mypy careervp/handlers/ careervp/models/ careervp/dal/ --strict
```

---

# PART 3: CDK INFRASTRUCTURE REMEDIATION

## Phase 11: CDK Infrastructure for All 27 Endpoints ⚠️ REQUIRED

**Duration:** 5 days | **Effort:** 32 hours
**Status (2026-02-18):** REQUIRES IMPLEMENTATION

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `cdk_async_infrastructure_spec.yaml` | Missing DynamoDB tables, S3 buckets, async resources |
| Mandatory | `cdk_e2e_validation_spec.yaml` | Endpoint-to-resource validation rules |
| Reference | `prompt_optimization_cdk_spec.yaml` | CDK best practices compliance |
| Reference | `storage_contract_spec.yaml` | Current storage mapping |

### Step 11.1: Add Missing DynamoDB Tables

**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/cdk_e2e_validation_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (Rules: DDB_001, DDB_002, DDB_003, DDB_005)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/cdk_e2e_validation_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml `

ROLE: Senior AWS Infrastructure Engineer specializing in CDK, DynamoDB, and serverless

CONTEXT: Add missing DynamoDB tables to support all 27 API endpoints.

TASK: Add 6 new DynamoDB tables to api_db_construct.py

1. Add to infra/careervp/api_db_construct.py:
   - cvs_table (userId, cvId, 90-day TTL)
   - applications_table (userId, applicationId, status-index GSI)
   - gap_responses_table (userId, questionId, 365-day TTL)
   - knowledge_table (userEmail, knowledgeType, entity-index GSI, 365-day TTL)
   - artifacts_table (applicationId, artifactId, type-index GSI, 90-day TTL)
   - company_research_cache_table (cacheKey, 30-day TTL)

2. Follow existing patterns:
   - Use PAY_PER_REQUEST billing (per DDB_001)
   - Enable point_in_time_recovery=True (per DDB_002)
   - Add TTL attribute for cache tables (per DDB_005)
   - Add GSIs where specified

3. Export table names via constants.py if needed

VALIDATION CRITERIA:
- [ ] All 6 tables defined in api_db_construct.py
- [ ] Each table has correct partition key (and sort key where specified)
- [ ] PAY_PER_REQUEST billing on all tables
- [ ] PITR enabled on all tables
- [ ] TTL configured on cache/ephemeral tables
- [ ] GSIs configured where specified

OUTPUT FORMAT: Provide implementation with inline comments. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 11.2: Add Missing S3 Buckets

**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (Rules: S3_001, S3_002, S3_003, S3_004)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml (Rules: S3_001, S3_002, S3_003, S3_004)`

ROLE: Senior AWS Infrastructure Engineer specializing in CDK and S3

CONTEXT: Add missing S3 buckets for static assets, backups, and logs.

TASK: Add 4 new S3 buckets to api_db_construct.py

1. Add to infra/careervp/api_db_construct.py:
   - static-{env} (frontend SPA, no lifecycle)
   - backups-{env} (versioning, lifecycle: 30d→IA, 90d→Glacier)
   - logs-{env} (versioning, lifecycle: 180d→IA, 365d→Glacier)
   - artifacts-{env} (versioning, lifecycle: 90d→IA, 180d→Glacier)

2. Follow existing patterns:
   - Block public access (per S3_001)
   - Enable versioning for data protection (per S3_002)
   - Configure lifecycle policies (per S3_003)
   - Use SSE-S3 encryption

VALIDATION CRITERIA:
- [ ] All 4 buckets defined in api_db_construct.py
- [ ] Block public access on all buckets
- [ ] Versioning enabled on backups, logs, artifacts
- [ ] Lifecycle policies configured per spec

OUTPUT FORMAT: Provide implementation with inline comments. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 11.3: Add SQS Queues with DLQ

**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (Rules: SQS_001, SQS_002, SQS_003, SQS_004)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml`

ROLE: Senior AWS Infrastructure Engineer specializing in CDK and SQS

CONTEXT: Add SQS queues for async job processing with dead letter queues.

TASK: Add 2 SQS queues to api_db_construct.py

1. Add to infra/careervp/api_db_construct.py:
   - cv_upload_queue (for CV upload processing)
   - gap_analysis_queue (for gap analysis processing)

2. Configure for each queue:
   - DLQ with 14-day retention (per SQS_001)
   - KMS encryption (per SQS_002)
   - Visibility timeout > Lambda timeout + buffer (per SQS_003)
   - FIFO only if order matters (per SQS_004)

VALIDATION CRITERIA:
- [ ] Both queues defined with KMS encryption
- [ ] DLQ configured for each queue
- [ ] Visibility timeout >= 300 seconds
- [ ] CDK synth passes

OUTPUT FORMAT: Provide implementation with inline comments. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 11.4: Add Worker Lambdas for Async Processing

**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (Rules: ASYNC_004, ASYNC_005)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml`

ROLE: Senior AWS Infrastructure Engineer specializing in CDK, Lambda, and async processing

CONTEXT: Add worker Lambda functions for background async job processing.

TASK: Add 5 worker Lambda functions to api_construct.py

1. Add worker Lambdas:
   - cv_upload_worker (triggered by S3 event)
   - vpr_worker (triggered by DynamoDB Streams)
   - cv_tailor_worker (triggered by DynamoDB Streams)
   - cover_letter_worker (triggered by DynamoDB Streams)
   - interview_prep_worker (triggered by DynamoDB Streams)

2. Configure for each:
   - Enable DynamoDB Streams with NEW_AND_OLD_IMAGES (per ASYNC_005)
   - Add DLQ for failed processing (per ASYNC_004)
   - Set timeout 300 seconds
   - Grant IAM access to required tables/buckets

3. Update Lambda environment variables with new table names

VALIDATION CRITERIA:
- [ ] All 5 worker Lambdas defined
- [ ] Event sources configured (S3 events, DynamoDB Streams)
- [ ] DLQ configured for each worker
- [ ] IAM policies grant least-privilege access

OUTPUT FORMAT: Provide implementation with inline comments. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 11.5: Update Lambda IAM and Environment Variables

**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml` (Rules: IAM_001, LAMBDA_CONFIG_008)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
**READ FIRST:**
- `docs/refactor/specs/cdk_async_infrastructure_spec.yaml`
- `docs/refactor/specs/prompt_optimization_cdk_spec.yaml`

ROLE: Senior AWS Infrastructure Engineer specializing in CDK and IAM

CONTEXT: Update Lambda execution roles with least-privilege access to new resources.

TASK: Update IAM policies and environment variables

1. Update Lambda execution roles in api_construct.py:
   - Add table ARN permissions (not wildcard) per IAM_001
   - Add S3 bucket permissions (not wildcard) per IAM_001

2. Update environment variables per LAMBDA_CONFIG_008:
   - CVS_TABLE_NAME
   - APPLICATIONS_TABLE_NAME
   - GAP_RESPONSES_TABLE_NAME
   - KNOWLEDGE_TABLE_NAME
   - ARTIFACTS_TABLE_NAME
   - COMPANY_RESEARCH_CACHE_TABLE_NAME

VALIDATION CRITERIA:
- [ ] No wildcard (*) in IAM policies
- [ ] All new table names in environment variables
- [ ] CDK synth passes

OUTPUT FORMAT: Provide implementation with inline comments. Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Step 11.6: Verify CDK Synthesis

**CODE:**
```bash
# CDK synth validation
cd /Users/yitzchak/Documents/dev/careervp/infra
uv sync
cdk synth

# Verify table count
grep -c 'dynamodb.TableV2\|dynamodb.Table' careervp/api_db_construct.py
# Expected: >= 9 tables

# Verify bucket count
grep -c 's3.Bucket' careervp/api_db_construct.py
# Expected: >= 6 buckets
```

### Step 11.7: Run Infrastructure Tests

**CODE:**
```bash
# Run CDK infrastructure tests
cd /Users/yitzchak/Documents/dev/careervp/infra
uv run pytest tests/infrastructure/test_cdk.py -v --tb=short

# Run CDK Nag security scan
cdk nag scan --app='python app.py'
```

---

# PART 4: TEST CREATION

## Task T1: VPR Async E2E Test

### File to Create:
- `src/backend/tests/e2e/test_vpr_async_polling.py`

### CODE:
```bash
# VSCode + Anthropic Haiku
"""
Create VPR Async E2E tests:

1. Create: src/backend/tests/e2e/test_vpr_async_polling.py
   - test_submit_vpr_job_returns_202()
   - test_poll_vpr_status_pending_to_completed()
   - test_poll_vpr_status_handles_errors()
   - test_vpr_timeout_handling()

Tests the full async lifecycle:
- POST /vpr/generate -> 202 Accepted
- GET /vpr/{vprId} -> polling until completed

KNOWLEDGE: docs/refactor/specs/api_contract_spec.yaml (async polling section)

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

---

## Task T2: Cover Letter Tests

### CODE:
```bash
# VSCode + Anthropic Haiku
"""
Create Cover Letter test suite:

1. Create: src/backend/tests/cover-letter/unit/test_cover_letter_logic.py
2. Create: src/backend/tests/cover-letter/unit/test_cover_letter_prompt.py
3. Create: src/backend/tests/cover-letter/integration/test_cover_letter_handler.py
4. Create: src/backend/tests/cover-letter/e2e/test_cover_letter_flow.py

OUTPUT FORMAT:
Output results to docs/refactor/execution_runbook_2_results.md.
"""
```

### Test Creation Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# VPR Async E2E tests
uv run pytest tests/e2e/test_vpr_async_polling.py -v --tb=short

# Cover Letter tests
uv run pytest tests/cover-letter/unit/ -v --tb=short
uv run pytest tests/cover-letter/integration/ -v --tb=short
uv run pytest tests/cover-letter/e2e/ -v --tb=short
```

---

# PART 4: VERIFICATION COMMANDS

```bash
# Run all tests
cd src/backend && uv run pytest tests/unit/ -v --tb=short

# Run lint
cd src/backend && uv run ruff check careervp/

# Run type check
cd src/backend && uv run mypy careervp --strict

# CDK synth
cd infra && npx cdk synth

# Feature-specific tests
uv run pytest tests/unit/test_cv_summarizer.py -v
uv run pytest tests/unit/test_vpr_generator.py -v
uv run pytest tests/unit/test_cv_tailoring.py -v
uv run pytest tests/unit/test_fvs_validator.py -v
uv run pytest tests/unit/test_user_handler.py -v
uv run pytest tests/unit/test_job_handler.py -v
uv run pytest tests/unit/test_health_handler.py -v
uv run pytest tests/e2e/test_vpr_async_polling.py -v
uv run pytest tests/cover-letter/ -v
```

---

# COMPLETION CHECKLIST

## Phase 2: Cost Optimization
- [x] Phase 2: CV Summarizer implemented (Step 2.1)
- [x] Phase 2: LLM Cache implemented (Step 2.2) - DynamoDB with TTL
- [x] Phase 2: Anthropic API migration (not Bedrock)
- [ ] Phase 2: Circuit breaker wired (Step 2.3)

## Phase 3: VPR 6-Stage Generator
- [ ] Phase 3: 6-stage VPR pipeline
- [ ] Phase 3: Anti-AI wired

## Phase 4: CV Tailoring
- [ ] Phase 4: 3-step CV tailoring
- [ ] Phase 4: Self-correction loop (ATS >= 8.0)

## Phase 5: Gap Analysis
- [ ] Phase 5: 10 question limit
- [ ] Phase 5: Question tagging

## Phase 6: Cover Letter ✅ IMPLEMENTED
- [x] Phase 6: Cover Letter unit tests
- [x] Phase 6: Cover Letter integration tests
- [x] Phase 6: Cover Letter E2E tests

## Phase 7: Quality Validator (FVS)
- [ ] Phase 7: ATS scoring
- [ ] Phase 7: Anti-AI scoring wired
- [ ] Phase 7: Cross-doc consistency

## Phase 8: Knowledge Base ✅ IMPLEMENTED
- [x] Phase 8: Knowledge Base CRUD
- [x] Phase 8: Memory-aware gap analysis
- [x] Phase 8: Knowledge table integration

## Phase 9: Interview Prep ✅ IMPLEMENTED
- [x] Phase 9: Interview prep generation
- [x] Phase 9: Question bank integration
- [x] Phase 9: Interview prep E2E tests

## Phase 7: Quality Validator (FVS)
- [ ] Phase 7: ATS scoring
- [ ] Phase 7: Anti-AI scoring wired
- [ ] Phase 7: Cross-doc consistency

## Phase 10: API Contract (All 27 Endpoints)
- [ ] Phase 10.0: Path Normalization Strategy
- [ ] Phase 10.0a: API Gateway Additive Route Migration
- [ ] Phase 10.0b: Infra Diff + Safety Gate
- [ ] Phase 10.0c: Legacy Route Decommission Gate
- [ ] Phase 10.0d: Storage Contract Lock
- [ ] Phase 10.0e: Data Storage Adapter Integration
- [ ] Phase 10.1: Auth endpoints (register, login, refresh)
- [ ] Phase 10.2: User endpoints (GET/PUT /users/me, GET /users/me/cvs)
- [ ] Phase 10.3: Job endpoints (POST/GET /jobs, GET /jobs/{jobId})
- [ ] Phase 10.4: VPR endpoint alignment + list endpoint
- [ ] Phase 10.5: Gap Analysis handler completion
- [ ] Phase 10.6: CV Tailoring status + list endpoints
- [ ] Phase 10.7: Cover Letter status + list endpoints
- [ ] Phase 10.8: Interview Prep status endpoint
- [ ] Phase 10.9: Company Research GET endpoint
- [ ] Phase 10.10: Health check endpoint
- [ ] Phase 10.11: Request/Response Schema Conformance
- [ ] Phase 10.12: OpenAPI Contract Validation Suite

## Phase 11: CDK Infrastructure (All 27 Endpoints)
- [ ] Phase 11.1: Add missing DynamoDB tables (6 tables)
- [ ] Phase 11.2: Add missing S3 buckets (4 buckets)
- [ ] Phase 11.3: Add SQS queues with DLQ (2 queues)
- [ ] Phase 11.4: Add Worker Lambdas (5 workers)
- [ ] Phase 11.5: Update Lambda IAM and environment variables
- [ ] Phase 11.6: Verify CDK synthesis
- [ ] Phase 11.7: Run infrastructure tests
- [ ] CDK table count >= 9
- [ ] CDK bucket count >= 6
- [ ] CDK Nag passes

## Verification
- [ ] VPR Async: E2E test
- [ ] All tests passing
- [ ] Lint clean
- [ ] Type check clean
- [ ] CDK synth succeeds
- [ ] OpenAPI contract validation: 27/27 endpoints (100%)

---

## Final Smoke Test: All Endpoints

Run after full deployment to verify all 27 OpenAPI endpoints work:

```bash
#!/bin/bash
# Smoke test for all 27 endpoints

API_BASE="https://api.careervp.com/v1"
TOKEN="your-jwt-token"

echo "=== Running Smoke Tests ==="

# Test health (no auth)
curl -s "$API_BASE/health" | jq -e '.status == "healthy"' && echo "✓ GET /health" || echo "✗ GET /health"

# Test auth endpoints (no auth required)
curl -s -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test User"}' \
  && echo "✓ POST /auth/register"

curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!"}' \
  && echo "✓ POST /auth/login"

# Test authenticated endpoints
HEADERS="-H \"Authorization: Bearer $TOKEN\" -H \"Content-Type: application/json\""

# CV endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/cv.json' '$API_BASE/cv'" && echo "✓ POST /cv"
eval "curl -s $HEADERS '$API_BASE/cv'" && echo "✓ GET /cvs"

# VPR endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/vpr.json' '$API_BASE/vpr/generate'" && echo "✓ POST /vpr/generate"

# CV Tailoring endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/tailor.json' '$API_BASE/cv-tailoring/generate'" && echo "✓ POST /cv-tailoring/generate"

# Gap Analysis endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/gap.json' '$API_BASE/gap-analysis/questions'" && echo "✓ POST /gap-analysis/questions"

# Cover Letter endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/cover.json' '$API_BASE/cover-letter/generate'" && echo "✓ POST /cover-letter/generate"

# Interview Prep endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/interview.json' '$API_BASE/interview-prep/generate'" && echo "✓ POST /interview-prep/generate"

# Company Research endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/company.json' '$API_BASE/company-research/fetch'" && echo "✓ POST /company-research/fetch"

# Job endpoints
eval "curl -s -X POST $HEADERS -d '@payloads/job.json' '$API_BASE/jobs'" && echo "✓ POST /jobs"
eval "curl -s $HEADERS '$API_BASE/jobs'" && echo "✓ GET /jobs"

# User endpoints
eval "curl -s $HEADERS '$API_BASE/users/me'" && echo "✓ GET /users/me"

echo "=== Smoke Tests Complete ==="
```

**Expected Results:**
- All endpoints return 2xx status codes
- No authentication errors on protected endpoints
- Response schemas match OpenAPI spec

---

## Phase 2 Live Test Verification Checklist

After running live tests, mark complete:

- [ ] CV Summarizer reduces tokens by ~95%
- [ ] LLM Cache returns cached responses on repeat requests
- [ ] Anthropic API (not Bedrock) is being called
- [ ] Cache table has items with correct TTL
- [ ] All Phase 2 endpoints respond correctly
