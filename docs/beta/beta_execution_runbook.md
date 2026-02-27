# CareerVP Beta Execution Runbook

**Version:** 1.0
**Date:** 2026-02-26
**Deadline:** 2026-03-11
**Author:** Senior DevOps Engineer
**Pattern Reference:** `docs/refactor/execution_runbook_2.md`

---

## READ FIRST

```
@spec docs/best_practices/yaml/prompt_optimization_spec.yaml
@spec docs/best_practices/yaml/lambda_handler_spec.yaml
@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml
@spec docs/best_practices/yaml/testing_spec.yaml
@spec docs/best_practices/yaml/cicd_spec.yaml
@spec docs/best_practices/yaml/cognito_spec.yaml
@spec docs/best_practices/yaml/trial_enforcement_spec.yaml
@spec docs/best_practices/yaml/application_state_spec.yaml
@ref  docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md
@pattern docs/refactor/execution_runbook_2.md
```

---

## Go/No-Go Claim

By **2026-03-11**, a user on `stage.careervp.com` can:
1. Register and authenticate via **Cognito**
2. Upload a CV and create a job application
3. Receive **AI-generated** gap analysis questions (not templates)
4. Submit gap responses
5. Retrieve five **AI-generated** artifacts (VPR, tailored CV, cover letter, interview prep, gap analysis)
6. Each artifact is **stored, listable, re-retrievable**
7. Under **TLS 1.2**, with **trial enforcement active** (14-day / 3-application limit)

**Launch blocked** unless all I1–I8 invariants pass with evidence < 24 hours old.

---

## Invariants Reference

| ID | Invariant | Evidence Artifact | Pass Metric |
|----|-----------|-------------------|-------------|
| I1 | Every generator calls Claude, no template output | `docs/beta/evidence/I1_generators/generator-output-audit.json` | 0 template matches in 50 runs |
| I2 | Every artifact persisted and listable | `docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json` | 100% roundtrip in 50 runs |
| I3 | Cognito JWT is sole identity source | `docs/beta/evidence/I3_auth/auth-abuse-matrix.json` | All 4 scenarios pass on all routes |
| I4 | No payload-based identity fallback | `docs/beta/evidence/I4_identity/identity-extraction-audit.txt` | 0 grep matches |
| I5 | Trial enforcement blocks app #4 and day-15 | `docs/beta/evidence/I5_trial/trial-enforcement-report.json` | All 3 sub-tests pass |
| I6 | Frontend state survives page reload | `docs/beta/evidence/I6_state/state-recovery-matrix.json` | 7/7 steps pass |
| I7 | One canonical route per operation | `docs/beta/evidence/I7_routes/route-surface-diff.txt` | Empty diff |
| I8 | Async SLAs met (VPR<90s, others<60s p95) | `docs/beta/evidence/I8_sla/async-sla-report.json` | All SLAs at p95 |

---

## Execution Order (Dependency Layers)

```
L0 (Generators) → L1 (Persistence) → L2 (Auth + Routes) → L3 (App State)
                                                          → L5 (Trial)
                                    → L6 (Route Cleanup)
L3 → L4 (Frontend) → L7 (Evidence)
L5 → L4 → L7
L8 (Operational Readiness) — requires all layers complete
```

**Critical path:** L0 → L1 → L3 → L4 → L7
**Cut trigger:** Day 9 (2026-03-07) — if L0 or L1 not complete, cut scope

---

## Frontend Dependency Map

Use marker `[FE]` for sections that require `src/frontend` and UI/E2E flows.

| Scope | Sections | Can Defer? | Current Status |
|------|----------|------------|----------------|
| Cognito client integration | L2.4 `[FE]` | Yes (backend can continue) | ⛔ Blocked (`src/frontend` missing) |
| UI workflow implementation | Phase 7 L7.1–L7.5 `[FE]` | Yes (run later as one wave) | ⛔ Deferred |
| Frontend reload invariant | I6 / E6 `[FE]` | No for final sign-off | Pending until frontend exists |

**Backend-first sequencing when frontend is unavailable:**
1. Complete L0, L1, L2.1–L2.3, L2.5, L3, L5, L6
2. Generate backend evidence (E1, E2, E3, E4, E5, E7, E8 where applicable)
3. Defer all `[FE]` sections (L2.4 + Phase 7 + E6)
4. Execute one frontend closure wave later, then re-run final evidence/sign-off

---

---

# Phase 1: Generator Reality (Layer 0)

**Purpose:** Fix broken AI generators that return templates instead of Claude API calls
**Invariant:** I1
**Preconditions Resolved:** PC1

---

### Step L0.1: Fix Cover Letter Handler to Call Claude API

**Duration:** 1 hour
**Invariant(s) Satisfied:** I1 (partial — cover letter generator)
**Precondition(s) Resolved:** PC1 (partial)
**Status:** ✅ Completed (2026-02-27, test-first RED → GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L0_1_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/refactor/specs/cover_letter_spec.yaml`
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`
- `@pattern docs/refactor/execution_runbook_2.md#step-2.1`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in AWS Lambda, Python, and Anthropic Claude API

CONTEXT:
- Current state: careervp/logic/cover_letter.py returns a stub string like
  "Generated cover letter for request {id}" — no Claude API call is made
- Target state: cover_letter.py calls self.llm_client.generate(prompt) with
  real CV + job context via cover_letter_prompt.py, returns structured output
- Impact: I1 fails today — beta launch blocked until all 5 generators produce
  real AI output

TASK: Replace the cover letter stub with a real LLMClient.generate() call
using the existing prompt templates in careervp/logic/prompts/cover_letter_prompt.py

IMPLEMENTATION DETAILS:

1. Modify: src/backend/careervp/logic/cover_letter.py
   - Locate the stub/placeholder that returns template strings
   - Replace with: prompt = CoverLetterPrompt.build(cv=cv_data, job=job_data)
   - Call: content = self.llm_client.generate(prompt, model="claude-haiku-4-5-20251001")
   - Return: CoverLetterOutput(content=content, word_count=len(content.split()),
     generated_at=datetime.now(timezone.utc).isoformat())
   - Wrap in try/except LLMError → return ResultCode.LLM_TIMEOUT
   - Wrap in try/except CircuitBreakerOpenError → return ResultCode.SERVICE_UNAVAILABLE

2. Verify: src/backend/careervp/handlers/cover_letter_handler.py
   - Confirm user_id extracted from event['requestContext']['authorizer']['claims']['sub']
   - Confirm result is persisted via DynamoDalHandler (not returned directly)
   - Confirm NO reference to X-User-Id header or payload user_id
   - Add: metrics.add_metric(name="CoverLetterGenerated", unit="Count", value=1)

3. Create: src/backend/tests/unit/test_l0_cover_letter_generation.py
   - test_cover_letter_calls_llm_client_generate: mock LLMClient, assert .generate() called
   - test_output_does_not_contain_template_placeholder_id: assert no template strings
   - test_returns_artifact_id: assert artifact_id in response body
   - test_llm_error_returns_503: mock LLMError → assert 503
   - test_wrong_user_cv_returns_403: wrong user_id → assert 403

PROHIBITED:
- DO NOT return any hardcoded string like "Generated cover letter for..."
- DO NOT read user_id from event body or X-User-Id header
- DO NOT call Bedrock — use LLMClient which wraps Anthropic SDK
- DO NOT use table.scan() in any persistence call

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r "Generated cover letter for request" src/backend/careervp/logic/ | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l0_cover_letter_generation.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/logic/cover_letter.py
- [ ] Run: cd src/backend && uv run mypy careervp/logic/cover_letter.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L0_1_results.md
- Include: before/after diff of the stub replaced, test run output, lint/type output
"""
```

**TEST:** `src/backend/tests/unit/test_l0_cover_letter_generation.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l0_generators_test.json` (key: `L0_1_cover_letter`)

---

### Step L0.2: Fix Interview Prep Handler to Call Claude API

**Duration:** 1 hour
**Invariant(s) Satisfied:** I1 (partial — interview prep generator)
**Precondition(s) Resolved:** PC1 (partial)
**Status:** ✅ Completed (2026-02-27, test-first RED → GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L0_2_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/refactor/specs/interview_prep_spec.yaml`
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in AWS Lambda, Python, and Anthropic Claude API

CONTEXT:
- Current state: interview_prep.py returns STAR template strings like
  "describe a relevant STAR example" — no Claude call made
- Target state: calls LLMClient.generate() with real CV + job context
- Impact: I1 fails — users see template output, not personalized interview prep

TASK: Replace interview prep stub with real LLMClient.generate() call

IMPLEMENTATION DETAILS:

1. Modify: src/backend/careervp/logic/interview_prep.py
   - Locate the STAR template stub returning hardcoded questions
   - Replace with: prompt = InterviewPrepPrompt.build(cv=cv_data, job=job_data)
   - Call: content = self.llm_client.generate(prompt, model="claude-haiku-4-5-20251001")
   - Parse the LLM response into structured InterviewPrepOutput with:
     * questions: list[InterviewQuestion] (each with question, category, tips)
     * generated_at: ISO8601 timestamp
   - Wrap in try/except LLMError, CircuitBreakerOpenError

2. Verify: src/backend/careervp/handlers/interview_prep_handler.py
   - user_id from requestContext.authorizer.claims.sub ONLY
   - Result persisted to DynamoDB via DynamoDalHandler
   - Async: if using SQS pattern, verify worker invoked correctly

3. Create: src/backend/tests/unit/test_l0_interview_prep_generation.py
   - test_interview_prep_calls_llm_client: assert .generate() invoked
   - test_no_star_template_in_output: assert no "describe a relevant STAR example"
   - test_no_template_in_output: assert no "Situation for question N"
   - test_returns_structured_questions: response has questions array
   - test_llm_error_returns_503

PROHIBITED:
- DO NOT return "describe a relevant STAR example" or "Situation for question"
- DO NOT hardcode STAR templates — generate via Claude
- DO NOT use X-User-Id header

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r "describe a relevant STAR example" src/backend/careervp/logic/ | wc -l → 0
- [ ] grep -r "Situation for question" src/backend/careervp/logic/ | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l0_interview_prep_generation.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/logic/interview_prep.py
- [ ] Run: cd src/backend && uv run mypy careervp/logic/interview_prep.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L0_2_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_l0_interview_prep_generation.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l0_generators_test.json` (key: `L0_2_interview_prep`)

---

### Step L0.3: Fix Gap Analysis Handler to Call Claude API

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I1 (partial), I5 (credit charge wired)
**Precondition(s) Resolved:** PC1 (partial)
**Status:** ✅ Completed (2026-02-27, test-first RED → GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L0_3_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/best_practices/yaml/trial_enforcement_spec.yaml`
- `@spec docs/refactor/specs/gap_analysis_spec.yaml`
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in AWS Lambda, Python, and Anthropic Claude API

CONTEXT:
- Current state: gap_handler.py returns parameterized template questions like
  "What quantifiable examples show your impact in core competency N"
- Target state: generates 10 AI questions across 4 tag categories using LLMClient
- Trial credit must be atomically charged BEFORE calling LLM (enforcement point)
- Impact: I1 and I5 both fail today — beta blocked

TASK: Replace gap analysis stub with real LLMClient.generate() + trial credit charge

IMPLEMENTATION DETAILS:

1. Modify: src/backend/careervp/logic/gap_analysis.py
   - Locate template question generation (parameterized "core competency N")
   - Replace with: prompt = GapAnalysisPrompt.build(cv=cv_data, job=job_data)
   - Call: response = self.llm_client.generate(prompt, model="claude-sonnet-4-6")
   - Parse JSON response into 10 GapQuestion objects:
     * question_id: str (UUID)
     * question: str (personalized, minimum 20 chars)
     * tag: one of ["CV IMPACT", "TECHNICAL", "BEHAVIORAL", "INTERVIEW/MVP"]
     * context: str (reference to specific CV/job element)
   - Validate: exactly 10 questions, all 4 tag categories represented

2. Modify: src/backend/careervp/handlers/gap_handler.py (POST gap-questions route)
   - Step 1: Extract user_id from Cognito claims
   - Step 2: Check trial status via TrialService.check_trial_status(user_id)
   - Step 3: Atomically charge credit via TrialService.consume_credit(user_id)
   - Step 4: Call gap_analysis.generate_questions(cv, job)
   - Step 5: Persist questions to DynamoDB
   - Step 6: Update application state to gap_questions_pending
   - Handle: TrialExhaustedException → 403 trial_exhausted
   - Handle: TrialExpiredException → 403 trial_expired

3. Create: src/backend/tests/unit/test_l0_gap_analysis_generation.py
   - test_gap_analysis_calls_llm_client
   - test_generates_10_questions
   - test_questions_have_valid_tags
   - test_questions_cover_all_4_categories
   - test_no_template_pattern_in_questions (parametrize over TEMPLATE_PATTERNS)
   - test_trial_credit_charged_before_llm_call
   - test_trial_exhausted_returns_403
   - test_trial_expired_returns_403

PROHIBITED:
- DO NOT return "What quantifiable examples show your impact in core competency N"
- DO NOT generate < 10 or > 10 questions
- DO NOT call LLM before charging trial credit
- DO NOT use X-User-Id header for identity

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r "core competency N" src/backend/careervp/ | wc -l → 0
- [ ] grep -r "What quantifiable examples show" src/backend/careervp/ | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l0_gap_analysis_generation.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/logic/gap_analysis.py
- [ ] Run: cd src/backend && uv run mypy careervp/logic/gap_analysis.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L0_3_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_l0_gap_analysis_generation.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l0_generators_test.json` (key: `L0_3_gap_analysis`)

---

### Step L0.4: Validate and Fix CV Tailoring Quality Scores

**Duration:** 2 hours
**Invariant(s) Satisfied:** I1 (partial — CV tailoring ATS score)
**Precondition(s) Resolved:** PC1 (partial)
**Status:** ✅ Completed (2026-02-27, test-first RED → GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L0_4_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/refactor/specs/cv_tailoring_spec.yaml`
- `@spec docs/refactor/specs/fvs_spec.yaml`
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in AI quality scoring and AWS Lambda

CONTEXT:
- Current state: CV Tailoring returns cv_id=null and ATS score=7 (target: >=8.0)
  Source: live-test-results3.log
- Target state: cv_id is always persisted (non-null), ATS score >= 8.0 at p95
- Impact: I1 fails (ATS score below target), I2 fails (cv_id null = not persisted)

TASK: Fix CV Tailoring to persist cv_id and achieve ATS score >= 8.0

IMPLEMENTATION DETAILS:

1. Diagnose: src/backend/careervp/logic/cv_tailoring.py
   - Find where cv_id is set to null — missing persistence step?
   - Check FVS validator ATS scoring: fvs_validator.py score_ats()
   - Identify self-correction loop: is it running max 3 iterations?

2. Fix cv_id persistence: src/backend/careervp/dal/cv_tailoring_dal.py
   - Ensure save_tailored_cv() returns the generated cv_id
   - Ensure cv_id is propagated back through cv_tailoring.py to the handler
   - Use DynamoDalHandler.put_item() (NOT CVTable)
   - Key schema: pk="USER#{user_id}", sk="ARTIFACT#CV_TAILORED#{cv_id}"

3. Fix ATS score: src/backend/careervp/logic/cv_tailoring_logic.py
   - Verify self-correction loop: if ats_score < 8.0, retry up to 3 times
   - Check: prompt includes job description keywords for ATS optimization
   - Check: FVS validator is called with the correct thresholds
   - If anti_ai_score < 9.0 or ats_score < 8.0 → trigger retry with feedback

4. Create: src/backend/tests/unit/test_l0_cv_tailoring_scores.py
   - test_cv_tailoring_returns_non_null_cv_id
   - test_cv_tailoring_ats_score_meets_threshold (>= 8.0)
   - test_cv_tailoring_anti_ai_score_meets_threshold (>= 9.0)
   - test_cv_tailoring_self_correction_triggers_on_low_score
   - test_cv_tailoring_max_3_correction_iterations

PROHIBITED:
- DO NOT set cv_id to null in any return path
- DO NOT skip FVS validation
- DO NOT use CVTable — use DynamoDalHandler
- DO NOT allow ATS score < 8.0 to pass without retry

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r "cv_id.*null\|cv_id.*None" src/backend/careervp/logic/cv_tailoring.py | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l0_cv_tailoring_scores.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/logic/cv_tailoring.py careervp/logic/cv_tailoring_logic.py
- [ ] Run: cd src/backend && uv run mypy careervp/logic/cv_tailoring.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L0_4_results.md
- Include: before/after ATS scores from test runs
"""
```

**TEST:** `src/backend/tests/unit/test_l0_cv_tailoring_scores.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l0_generators_test.json` (key: `L0_4_cv_tailoring`)

---

### Step L0.5: Reduce Company Research Latency to < 90s p95

**Duration:** 2 hours
**Invariant(s) Satisfied:** I8 (company research SLA)
**Precondition(s) Resolved:** PC1 (partial)
**Status:** ✅ Completed (2026-02-27, test-first RED → GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L0_5_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/refactor/specs/company_research_model_spec.yaml`
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: Senior Backend Engineer specializing in AWS Lambda performance optimization

CONTEXT:
- Current state: company research takes 150 seconds (measured in live-test-results3.log)
- Target state: p95 < 90 seconds
- Root cause candidates: synchronous web scraping, uncached LLM calls, serial processing
- Impact: I8 SLA fails — 150s exceeds any reasonable UX threshold

TASK: Reduce company research latency to < 90s at p95

IMPLEMENTATION DETAILS:

1. Profile: src/backend/careervp/logic/company_research.py
   - Time each step: web_search, web_scraper, llm_client.generate
   - Identify the dominant latency contributor

2. Optimize web scraping: src/backend/careervp/logic/utils/web_scraper.py
   - Add timeout: requests.get(url, timeout=10) — never block indefinitely
   - Parallelize: use asyncio.gather() or ThreadPoolExecutor for multi-URL scraping
   - Limit: scrape max 3 URLs, not unlimited

3. Add LLM caching: src/backend/careervp/logic/llm_cache.py
   - Cache company research results keyed by company_name (TTL: 7 days)
   - Cache hit → return immediately without LLM call
   - Cache miss → call LLM, store result

4. Reduce prompt size via CV summarizer: src/backend/careervp/logic/cv_summarizer.py
   - If CV > 3000 tokens, summarize before including in company research prompt

5. Create: src/backend/tests/unit/test_l0_company_research_latency.py
   - test_web_scraper_has_timeout: assert requests.get called with timeout kwarg
   - test_web_scraper_limits_to_3_urls: assert only 3 URLs scraped max
   - test_cache_hit_skips_llm_call: cached response → LLM not invoked
   - test_cache_miss_calls_llm: no cache → LLM invoked and result cached

PROHIBITED:
- DO NOT make unlimited web requests without timeout
- DO NOT scrape more than 5 URLs in sequence
- DO NOT skip caching for repeated company lookups

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l0_company_research_latency.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/logic/company_research.py
- [ ] Run: cd src/backend && uv run mypy careervp/logic/company_research.py --strict
- [ ] Manual: run company_research against real company, measure wall time < 90s

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L0_5_results.md
- Include: profiling output showing time per step before and after
"""
```

**TEST:** `src/backend/tests/unit/test_l0_company_research_latency.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l0_generators_test.json` (key: `L0_5_company_research`)

---

### Phase 1 Integration Test

**Description:** Run all 5 generators, scan all outputs for template patterns, assert 0 matches
**Status:** ✅ Completed (2026-02-27, integration audit GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L0_phase_integration_results.md`

**TEST:** `src/backend/tests/integration/test_l0_phase_integration.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l0_generators_test.json` (key: `phase_integration_test`)
**EVIDENCE:** `docs/beta/evidence/I1_generators/generator-output-audit.json`

```bash
cd src/backend && uv run pytest tests/integration/test_l0_phase_integration.py -v --tb=short -m integration
```

**Pass criterion:** 0 template pattern matches across 50 runs × 5 generators = 250 total runs

---

---

# Phase 2: Persistence and Data Integrity (Layer 1)

**Purpose:** Ensure all generated artifacts are stored in DynamoDB and retrievable via list endpoints
**Invariant:** I2
**Preconditions Resolved:** PC2, PC5, PC6

---

### Step L1.1: Fix Artifact Persistence to DynamoDB

**Duration:** 2 hours
**Invariant(s) Satisfied:** I2 (partial — persistence write)
**Precondition(s) Resolved:** PC2 (partial)
**Status:** ✅ Completed (2026-02-27, test-first RED → GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L1_1_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml`
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/refactor/specs/storage_contract_spec.yaml`
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in AWS DynamoDB and serverless persistence

CONTEXT:
- Current state: list endpoints return empty arrays after generation
  (e.g., GET /vprs returns vprs:[] even after successful VPR generation)
  Source: live-test-results3.log
- Target state: 100% roundtrip success — generate → poll → list → ID in array
- Root cause: artifact workers likely generate content but do not call DynamoDalHandler.put_item()
- Impact: I2 fails — artifacts are ephemeral, not stored

TASK: Ensure every artifact type is persisted to DynamoDB after generation with correct key schema

IMPLEMENTATION DETAILS:

1. Audit all artifact generators for missing DynamoDB write:
   - src/backend/careervp/handlers/vpr_worker_handler.py
   - src/backend/careervp/handlers/cover_letter_handler.py
   - src/backend/careervp/handlers/interview_prep_handler.py
   - src/backend/careervp/handlers/cv_tailoring_handler.py
   - src/backend/careervp/handlers/gap_handler.py

2. For each missing persistence call, add:
   dal = DynamoDalHandler(table_name=TABLE_NAME)
   dal.put_item({
       "pk": f"USER#{user_id}",
       "sk": f"ARTIFACT#{ARTIFACT_TYPE}#{artifact_id}",
       "artifact_id": artifact_id,
       "user_id": user_id,
       "job_id": job_id,
       "status": "completed",
       "content": generated_content,
       "created_at": datetime.now(timezone.utc).isoformat(),
       "entity_type": ARTIFACT_TYPE,
       "ttl": _ttl_timestamp(days=730),  # 2 years
   })

3. Verify list endpoints query correctly:
   - List endpoint must use Query (not Scan)
   - KeyConditionExpression: pk = USER#{user_id} AND begins_with(sk, ARTIFACT#TYPE#)
   - Must return artifact_id in response body

4. Create: src/backend/tests/unit/test_l1_artifact_persistence.py
   - test_cover_letter_persisted_to_dynamodb: mock dal, assert put_item called
   - test_vpr_persisted_to_dynamodb
   - test_cv_tailoring_persisted_to_dynamodb
   - test_interview_prep_persisted_to_dynamodb
   - test_gap_analysis_persisted_to_dynamodb
   - test_list_endpoint_returns_artifact_after_persist: insert record, call list, assert in response
   - test_list_uses_query_not_scan: assert table.scan never called

PROHIBITED:
- DO NOT use CVTable for any artifact persistence
- DO NOT use table.scan() — always Query with KeyConditionExpression
- DO NOT set artifact_id to null
- DO NOT skip TTL on artifact records

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r "table.scan\|\.scan(" src/backend/careervp/ | grep -v test | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l1_artifact_persistence.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/handlers/
- [ ] Run: cd src/backend && uv run mypy careervp/handlers/ --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L1_1_results.md
- Include: list of handlers modified, before/after test results
"""
```

**TEST:** `src/backend/tests/unit/test_l1_artifact_persistence.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l1_persistence_test.json` (key: `L1_1_artifact_persistence`)

---

### Step L1.2: Replace CVTable with DynamoDalHandler

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I2 (silent failure eliminated)
**Precondition(s) Resolved:** PC6
**Status:** ✅ Completed (2026-02-27, strict test-first validation GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L1_2_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml`
- `@spec docs/refactor/specs/storage_contract_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in DynamoDB data access patterns

CONTEXT:
- Current state: CVTable and DynamoDalHandler coexist — CVTable silently fails
  on missing data instead of raising errors (REFACTOR2_PLAN.md documents this)
- Target state: zero CVTable references — all handlers use DynamoDalHandler
- Impact: Silent failures make I2 impossible to verify

TASK: Migrate all CVTable usages to DynamoDalHandler across all handlers and DAL files

IMPLEMENTATION DETAILS:

1. Find all CVTable usages:
   grep -r "CVTable\|from careervp.dal.cv_table\|import CVTable" src/backend/careervp/

2. For each file found, replace CVTable calls with DynamoDalHandler equivalent:
   - CVTable.get_cv(cv_id) → dal.get_item(pk=f"USER#{user_id}", sk=f"CV#{cv_id}")
   - CVTable.save_cv(cv) → dal.put_item({pk: ..., sk: ..., ...cv_fields})
   - CVTable.list_cvs(user_id) → dal.query(pk=f"USER#{user_id}", sk_prefix="CV#")

3. Update src/backend/careervp/dal/cv_dal.py if it wraps CVTable:
   - Replace the underlying CVTable calls with DynamoDalHandler
   - Maintain the same public interface (cv_dal.py still callable)

4. Create: src/backend/tests/unit/test_l1_dal_unification.py
   - test_no_cvtable_imports_in_handlers: grep returns 0 matches
   - test_cv_dal_uses_dynamo_dal_handler: assert CVDal uses DynamoDalHandler internally
   - test_cv_get_returns_correct_data: mock dal.get_item, assert CVDal.get_cv works

PROHIBITED:
- DO NOT modify the public API of cv_dal.py (handlers call it)
- DO NOT delete cv_dal.py — just replace its internals
- DO NOT use CVTable anywhere

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r "CVTable(" src/backend/careervp/ | wc -l → 0
- [ ] grep -r "from careervp.dal.cv_table" src/backend/careervp/ | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l1_dal_unification.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/dal/
- [ ] Run: cd src/backend && uv run mypy careervp/dal/ --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L1_2_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_l1_dal_unification.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l1_persistence_test.json` (key: `L1_2_dal_unification`)

---

### Step L1.3: Fix Health Check to Report Real Infrastructure

**Duration:** 30 minutes
**Invariant(s) Satisfied:** I2 (health check accuracy)
**Precondition(s) Resolved:** PC5
**Status:** ✅ Completed (2026-02-27, strict test-first validation GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L1_3_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: Backend Engineer specializing in AWS Lambda observability

CONTEXT:
- Current state: health_handler.py reports "bedrock": "healthy" — stale after
  migration to Anthropic SDK. DynamoDB connectivity not validated.
- Target state: reports "anthropic": "healthy|degraded", "dynamodb": "healthy|degraded"
  by making real connectivity checks

TASK: Update health_handler.py to check actual Anthropic API and DynamoDB status

IMPLEMENTATION DETAILS:

1. Modify: src/backend/careervp/handlers/health_handler.py
   - Remove: "bedrock" health check
   - Add: Anthropic check — call anthropic_client.models.list() with 3s timeout
     * success → "anthropic": "healthy"
     * timeout/error → "anthropic": "degraded", log the error
   - Add: DynamoDB check — call dal.health_check() → describe_table with 2s timeout
     * success → "dynamodb": "healthy"
     * error → "dynamodb": "degraded"
   - Response: {"status": "healthy|degraded", "services": {"anthropic": ..., "dynamodb": ...}}
   - Route is PUBLIC (no Cognito auth required)

2. Create: src/backend/tests/unit/test_l1_health_check.py
   - test_health_reports_anthropic_not_bedrock: assert "bedrock" not in response body
   - test_health_reports_anthropic_healthy_on_success: mock success → "healthy"
   - test_health_reports_anthropic_degraded_on_error: mock error → "degraded"
   - test_health_reports_dynamodb_healthy: mock describe_table → "healthy"
   - test_health_returns_200_even_when_degraded: degraded services → 200 (not 500)

PROHIBITED:
- DO NOT report "bedrock" as a service
- DO NOT return 500 on degraded status — always 200 with status field
- DO NOT require auth on /health endpoint

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r '"bedrock"' src/backend/careervp/handlers/health_handler.py | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l1_health_check.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/handlers/health_handler.py

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L1_3_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_l1_health_check.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l1_persistence_test.json` (key: `L1_3_health_check`)

---

### Step L1.4: Validate List Endpoints Return Generated Artifacts

**Duration:** 1 hour
**Invariant(s) Satisfied:** I2 (list endpoint roundtrip)
**Precondition(s) Resolved:** PC2
**Status:** ✅ Completed (2026-02-27, strict test-first validation GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L1_4_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml`
- `@spec docs/refactor/specs/storage_contract_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in DynamoDB query patterns and REST APIs

CONTEXT:
- Current state: GET /vprs, GET /cover-letters, GET /cv-tailorings return []
  even after successful generation. Source: live-test-results3.log
- Target state: list endpoints return non-empty array with artifact_id matching
  what was returned by the generate endpoint

TASK: Fix all 5 list endpoints to correctly query and return persisted artifacts

IMPLEMENTATION DETAILS:

1. Audit each list endpoint handler (returns [] currently):
   - src/backend/careervp/handlers/vpr_handler.py (GET /vprs)
   - src/backend/careervp/handlers/cover_letter_handler.py (GET /cover-letters)
   - src/backend/careervp/handlers/cv_tailoring_handler.py (GET /cv-tailorings)
   - src/backend/careervp/handlers/interview_prep_handler.py (GET /interview-preps)
   - src/backend/careervp/handlers/gap_handler.py (GET /gap-analyses)

2. For each handler, ensure:
   - Uses DynamoDalHandler.query(pk=f"USER#{user_id}", sk_prefix=f"ARTIFACT#{TYPE}#")
   - Returns: {"items": [{artifact_id, status, created_at, job_id, ...}], "count": N}
   - Handles empty result: return {"items": [], "count": 0} (NOT [])
   - Handles pagination via LastEvaluatedKey

3. Create: src/backend/tests/unit/test_l1_list_endpoints.py
   For each of the 5 artifact types:
   - test_{type}_list_returns_empty_on_no_artifacts: no DB records → {"items": [], "count": 0}
   - test_{type}_list_returns_artifact_after_insert: pre-insert → list → assert artifact_id present
   - test_{type}_list_uses_query_not_scan: assert table.scan() never called
   - test_{type}_list_requires_auth: no Cognito claims → 401

PROHIBITED:
- DO NOT use table.scan() for list operations
- DO NOT return raw [] — return {"items": [], "count": 0}
- DO NOT return other users' artifacts — filter by user_id via pk

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -r "\.scan(" src/backend/careervp/handlers/ | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l1_list_endpoints.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/handlers/
- [ ] Run: cd src/backend && uv run mypy careervp/handlers/ --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L1_4_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_l1_list_endpoints.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l1_persistence_test.json` (key: `L1_4_list_endpoints`)

---

### Phase 2 Integration Test

**Description:** Generate artifact → poll complete → list → assert artifact_id in response
**Status:** ✅ Completed (2026-02-27, strict test-first integration GREEN on `beta/exec-runbk`)
**Execution Result:** `docs/beta/execution_results/L1_phase_integration_results.md`

**TEST:** `src/backend/tests/integration/test_l1_phase_integration.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l1_persistence_test.json` (key: `phase_integration_test`)
**EVIDENCE:** `docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json`

**Pass criterion:** 100% roundtrip success for all 5 artifact types across 50 runs

---

---

# Phase 3: Auth Migration (Layer 2)

**Purpose:** Migrate from custom JWT authorizer to Cognito JWT authorizer; remove all identity fallbacks
**Invariants:** I3, I4
**Preconditions Resolved:** PC3, PC4

---

### Step L2.1: Create CDK Cognito User Pool

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I3 (Cognito infrastructure)
**Precondition(s) Resolved:** PC4
**Status:** ✅ Completed (2026-02-27, strict test-first RED → GREEN on `beta/exec-runbook3`)
**Execution Result:** `docs/beta/execution_results/L2_1_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/cognito_spec.yaml`
- `@spec docs/best_practices/yaml/cicd_spec.yaml`
- `@pattern infra/careervp/api_construct.py`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior AWS CDK Engineer specializing in Cognito User Pools and API Gateway

CONTEXT:
- Current state: custom Lambda JWT authorizer (api_gateway_authorizer.py)
  Cognito not deployed; auth never tested with real tokens
- Target state: Cognito User Pool deployed, API Gateway uses Cognito JWT authorizer
- Impact: I3 and I4 both fail today — auth never tested end-to-end

TASK: Create Cognito User Pool CDK construct and deploy to dev/staging

IMPLEMENTATION DETAILS:

1. Create: infra/careervp/cognito_construct.py
   - Class: CognitoConstruct(Construct)
   - Deploys CognitoUserPool with: email sign-in, auto-verify, 8-char password policy
   - Deploys UserPoolClient: no secret, SRP + refresh token flows, 1h access token
   - Deploys domain: careervp-{env}.auth.{region}.amazoncognito.com
   - Exposes: user_pool, user_pool_client, user_pool_id, client_id as properties
   - Environment: pass env name as constructor param

2. Modify: infra/careervp/service_stack.py
   - Import and instantiate CognitoConstruct
   - Pass user_pool to api_construct for authorizer creation
   - Output: UserPoolId and ClientId as CloudFormation outputs

3. Create: src/backend/tests/infrastructure/test_l2_cognito_user_pool.py
   (CDK assertion test)
   - test_user_pool_created: Template has AWS::Cognito::UserPool
   - test_password_policy_minimum_8_chars: PasswordPolicy.MinimumLength == 8
   - test_user_pool_client_no_secret: GenerateSecret == false
   - test_email_verification_enabled: AutoVerifiedAttributes contains "email"

4. CDK Commands:
   cd infra && uv run cdk synth --app='python app.py'
   cd infra && uv run cdk diff CareervpStack-dev
   cd infra && uv run cdk deploy CareervpStack-dev --require-approval never

PROHIBITED:
- DO NOT generate client secret (web apps can't store secrets)
- DO NOT disable email verification
- DO NOT use deprecated Cognito patterns

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd infra && uv run cdk synth --app='python app.py' (must succeed)
- [ ] Run: cd src/backend && uv run pytest tests/infrastructure/test_l2_cognito_user_pool.py -v
- [ ] AWS Console: Cognito User Pool visible in dev account
- [ ] Manual: register test user, receive verification email

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L2_1_results.md
- Include: CDK synth output, CloudFormation outputs (UserPoolId, ClientId)
"""
```

**TEST:** `src/backend/tests/infrastructure/test_l2_cognito_user_pool.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l2_auth_scenarios_test.json` (key: `L2_1_cognito_user_pool`)

---

### Step L2.2: Configure API Gateway Cognito Authorizer

**Duration:** 1 hour
**Invariant(s) Satisfied:** I3 (authorizer configured)
**Precondition(s) Resolved:** PC3, PC4
**Status:** ✅ Completed (2026-02-27, strict test-first RED → GREEN on `beta/exec-runbook3`)
**Execution Result:** `docs/beta/execution_results/L2_2_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/cognito_spec.yaml`
- `@pattern infra/careervp/api_construct.py`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior AWS CDK Engineer specializing in API Gateway authorizers

CONTEXT:
- Current state: api_construct.py uses custom Lambda authorizer (api_gateway_authorizer.py)
- Target state: all protected routes use CognitoUserPoolsAuthorizer
- Impact: I3 requires Cognito as sole identity source — custom authorizer must be removed

TASK: Replace custom Lambda JWT authorizer with CognitoUserPoolsAuthorizer in CDK

IMPLEMENTATION DETAILS:

1. Modify: infra/careervp/api_construct.py
   - Add parameter: user_pool: cognito.UserPool
   - Create: CognitoUserPoolsAuthorizer(self, "CognitoAuth",
       cognito_user_pools=[user_pool],
       identity_source="method.request.header.Authorization")
   - Apply to ALL protected route .add_method() calls
   - Public routes (GET /health, POST /auth/*) use AuthorizationType.NONE explicitly
   - Remove: Lambda authorizer resource and integration
   - Remove: custom authorizer Lambda from Lambda function list

2. Create: src/backend/tests/infrastructure/test_l2_api_gateway_authorizer.py
   - test_cognito_authorizer_created: Template has AWS::ApiGateway::Authorizer type COGNITO_USER_POOLS
   - test_authorizer_on_protected_routes: All non-health, non-auth routes have authorizer
   - test_health_route_has_no_auth: GET /health has AuthorizationType NONE
   - test_auth_routes_have_no_auth: POST /auth/* have AuthorizationType NONE

PROHIBITED:
- DO NOT leave custom Lambda authorizer active alongside Cognito
- DO NOT apply Cognito auth to /health or /auth/* routes
- DO NOT hardcode User Pool ID — use parameter reference

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd infra && uv run cdk synth --app='python app.py'
- [ ] Run: cd src/backend && uv run pytest tests/infrastructure/test_l2_api_gateway_authorizer.py -v
- [ ] Manual: curl without token to protected route → 401

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L2_2_results.md
"""
```

**TEST:** `src/backend/tests/infrastructure/test_l2_api_gateway_authorizer.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l2_auth_scenarios_test.json` (key: `L2_2_api_gateway_authorizer`)

---

### Step L2.3: Remove X-User-Id Header and Payload Identity Extraction

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I4 (no identity fallback)
**Precondition(s) Resolved:** PC3
**Status:** ✅ Completed (2026-02-27, strict test-first RED → GREEN on `beta/exec-runbook3.1`)
**Execution Result:** `docs/beta/execution_results/L2_3_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/cognito_spec.yaml`
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Security Engineer specializing in AWS Lambda identity patterns

CONTEXT:
- Current state: some handlers may read X-User-Id header or extract user_id from
  request body as fallback when Cognito claims are absent
- Target state: ALL handlers extract user_id ONLY from
  event['requestContext']['authorizer']['claims']['sub']
- Impact: I4 requires static grep = 0 matches. Any fallback is a security vulnerability.

TASK: Audit and fix all handlers to use canonical Cognito identity extraction only

IMPLEMENTATION DETAILS:

1. Run static analysis grep:
   grep -rn "X-User-Id" src/backend/careervp/handlers/
   grep -rn "event.get.*user_id\|payload.*user_id\|body.*user_id" src/backend/careervp/handlers/
   grep -rn "requestContext.*identity\|principalId" src/backend/careervp/handlers/

2. For each match found, replace with canonical pattern:
   user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
   if not user_id:
       return _build_response(HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})

3. Extract into shared helper: src/backend/careervp/handlers/auth_utils.py
   def extract_user_id(event: dict) -> str | None:
       try:
           return event["requestContext"]["authorizer"]["claims"]["sub"]
       except (KeyError, TypeError):
           return None

4. Ensure all handlers import and call extract_user_id(event) from auth_utils

5. Create: src/backend/tests/unit/test_cognito_middleware.py
   (already created as skeleton — implement the RED-phase tests)
   - test_extracts_sub_from_cognito_claims
   - test_returns_none_when_no_authorizer
   - test_does_not_read_x_user_id_header
   - test_does_not_read_body_user_id

PROHIBITED:
- DO NOT use X-User-Id header in any handler
- DO NOT read user_id from request body or query string
- DO NOT use event.get('requestContext', {}).get('identity') legacy pattern

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -rn "X-User-Id" src/backend/careervp/handlers/ | wc -l → 0
- [ ] grep -rn "payload.*user_id\|body.*user_id" src/backend/careervp/handlers/ | wc -l → 0
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_cognito_middleware.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/handlers/auth_utils.py
- [ ] Run: cd src/backend && uv run mypy careervp/handlers/auth_utils.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L2_3_results.md
- Include: grep outputs (must be empty), list of handlers modified
- Generate: docs/beta/evidence/I4_identity/identity-extraction-audit.txt
"""
```

**TEST:** `src/backend/tests/unit/test_cognito_middleware.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l2_auth_scenarios_test.json` (key: `L2_3_identity_extraction`)

---

### Step L2.4 [FE]: Update Frontend with Cognito SDK

**Duration:** 2 hours
**Invariant(s) Satisfied:** I3 (frontend sends valid JWT)
**Status:** ⛔ Blocked (2026-02-27, `src/frontend` not present in this repository)
**Execution Result:** _Not executable in current workspace_

**READ FIRST:**
- `@spec docs/best_practices/yaml/cognito_spec.yaml`
- `@spec docs/best_practices/yaml/frontend_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Frontend Engineer specializing in React, TypeScript, and AWS Cognito SDK

CONTEXT:
- Current state: no frontend exists; Cognito not integrated
- Target state: frontend sends Cognito access tokens as Authorization: Bearer <token>
  on all protected API calls
- Impact: without valid tokens, I3 cannot be tested end-to-end

TASK: Implement Cognito auth module in the frontend with login, register, token refresh

IMPLEMENTATION DETAILS:

1. Install: npm install @aws-amplify/auth (or amazon-cognito-identity-js)

2. Create: src/frontend/src/auth/cognitoConfig.ts
   - Export: USER_POOL_ID, CLIENT_ID (from env vars NEXT_PUBLIC_*)
   - Configure Amplify.configure() with Auth settings

3. Create: src/frontend/src/auth/authService.ts
   - signUp(email, password, name): calls Auth.signUp()
   - signIn(email, password): calls Auth.signIn(), stores tokens
   - signOut(): calls Auth.signOut()
   - getAccessToken(): calls Auth.currentSession() → returns AccessToken.getJwtToken()
   - refreshSession(): auto-refresh via Auth.currentAuthenticatedUser()

4. Create: src/frontend/src/auth/useAuth.ts (React hook)
   - Returns: { user, isAuthenticated, isLoading, signIn, signOut, signUp }
   - Stores user session in React state
   - Auto-refreshes token before expiry

5. Create: src/frontend/src/api/apiClient.ts
   - Axios instance with interceptor: adds Authorization: Bearer {token} to all requests
   - Intercepts 401 → triggers token refresh → retries request

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] npm run build (no TypeScript errors)
- [ ] Manual: register new user → verify email → login → JWT visible in Network tab
- [ ] Manual: call protected API endpoint → 200 with valid token, 401 without

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L2_4_results.md
- Include: screenshot of successful auth flow (or console output)
"""
```

**TEST:** Frontend TypeScript tests (Jest/Vitest): `src/frontend/src/auth/__tests__/authService.test.ts`
**PAYLOAD:** `docs/refactor/payloads/beta_l2_auth_scenarios_test.json` (key: `auth_scenarios`)

---

### Step L2.5: Integration Test All Auth Scenarios

**Duration:** 1 hour
**Invariant(s) Satisfied:** I3 (all 4 scenarios), I4
**Precondition(s) Resolved:** PC3
**Status:** ✅ Completed (2026-02-27, test-first RED → GREEN on `beta/exec-runbook3.1`)
**Execution Result:** `docs/beta/execution_results/L2_5_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/cognito_spec.yaml`
- `@spec docs/best_practices/yaml/testing_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior QA Engineer specializing in security testing and auth integration

CONTEXT:
- Precondition: L2.1 (Cognito deployed), L2.2 (API Gateway authorizer active)
- Task: test all 4 auth scenarios against every protected route

TASK: Create integration test suite for all 4 auth scenarios

IMPLEMENTATION DETAILS:

1. Create: src/backend/tests/integration/test_l2_auth_integration.py
   For each protected route in beta_l2_auth_scenarios_test.json#protected_routes:
   - Scenario A (no_token): Request with no Authorization header → assert 401
   - Scenario B (expired_token): Mock missing claims → assert 401
   - Scenario C (wrong_user): Valid JWT for user-A, resource owned by user-B → assert 403
   - Scenario D (valid_token): Valid JWT for resource owner → assert 200

2. Generate evidence: docs/beta/evidence/I3_auth/auth-abuse-matrix.json
   Format: {"route": "/vprs", "method": "GET", "scenario": "no_token",
            "expected": 401, "actual": 401, "pass": true}

3. Generate evidence: docs/beta/evidence/I4_identity/identity-extraction-audit.txt
   Format: output of grep commands (must be empty)

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/integration/test_l2_auth_integration.py -v -m integration
- [ ] Evidence: auth-abuse-matrix.json exists with all routes, all scenarios, all pass=true
- [ ] Evidence: identity-extraction-audit.txt exists and is empty

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L2_5_results.md
- Write evidence: docs/beta/evidence/I3_auth/auth-abuse-matrix.json
- Write evidence: docs/beta/evidence/I4_identity/identity-extraction-audit.txt
"""
```

**TEST:** `src/backend/tests/integration/test_l2_auth_integration.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l2_auth_scenarios_test.json`

---

### Phase 3 Integration Test

**Description:** Test all 4 auth scenarios (no token, expired, wrong user, valid) against all protected routes

**Evidence:** `docs/beta/evidence/I3_auth/auth-abuse-matrix.json`

```bash
cd src/backend && uv run pytest tests/integration/test_l2_auth_integration.py -v --tb=short -m integration
```

---

---

# Phase 4: Application State Model (Layer 3)

**Purpose:** Implement canonical lifecycle model enabling state recovery on page reload
**Invariant:** I6
**Preconditions Resolved:** PC2 (application state stored)

---

### Step L3.1: Design Application DynamoDB Schema

**Duration:** 1 hour
**Invariant(s) Satisfied:** I6 (state storage foundation)

**READ FIRST:**
- `@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml`
- `@spec docs/best_practices/yaml/application_state_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Data Architect specializing in DynamoDB single-table design

CONTEXT:
- Current state: no application state model exists — page reload loses all workflow state
- Target state: application records stored in DynamoDB with 7-state lifecycle model
- Schema: pk=USER#{user_id}, sk=APP#{application_id}

TASK: Implement application DynamoDB repository with full CRUD for 7-state lifecycle

IMPLEMENTATION DETAILS:

1. Create: src/backend/careervp/dal/application_repository.py
   - Class: ApplicationRepository(dal: DynamoDalHandler)
   - create(user_id, job_id) -> str (application_id)
   - get(application_id, user_id) -> dict | None
   - update_state(application_id, user_id, new_state, expected_state) -> None
   - update_cv(application_id, user_id, cv_id) -> None
   - update_artifact_status(application_id, user_id, artifact_type, status) -> None
   - Uses ConditionExpression for all state transitions
   - Schema from application_state_spec.yaml Section 2

2. Create: src/backend/careervp/models/application.py (if not exists)
   - Pydantic models: Application, ApplicationState (enum), ArtifactStatus (enum)
   - ApplicationCreateRequest, ApplicationRecoveryResponse

3. CDK: add state-index GSI to users table in infra/careervp/api_db_construct.py
   - GSI: pk=state, sk=updated_at

4. Create: src/backend/tests/unit/test_l3_application_schema.py
   - test_application_created_with_correct_schema
   - test_application_initial_state_is_created
   - test_state_transition_uses_condition_expression
   - test_invalid_transition_raises_error
   - test_backward_transition_blocked

PROHIBITED:
- DO NOT use table.scan() for any application query
- DO NOT allow backward state transitions
- DO NOT skip ConditionExpression on state updates

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l3_application_schema.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/dal/application_repository.py
- [ ] Run: cd src/backend && uv run mypy careervp/dal/application_repository.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L3_1_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_application_state.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l3_application_state_test.json` (key: `L3_1_schema`)

---

### Step L3.2: Implement GET /applications/{id} Recovery Endpoint

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I6 (recovery endpoint)

**READ FIRST:**
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`
- `@spec docs/best_practices/yaml/application_state_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in REST API design and AWS Lambda

CONTEXT:
- Current state: no /applications/{id} endpoint exists
- Target state: single endpoint returns full state needed for page-reload recovery
  (application + job + cv + gap questions/responses + artifact statuses)

TASK: Implement GET /applications/{id} recovery endpoint

IMPLEMENTATION DETAILS:

1. Create: src/backend/careervp/handlers/application_handler.py
   - Route: GET /applications/{application_id}
   - Powertools decorators: @logger.inject_lambda_context, @tracer.capture_lambda_handler, @metrics.log_metrics
   - Extract: user_id = extract_user_id(event) from Cognito claims ONLY
   - Ownership check: application.user_id == user_id → else 403
   - Build recovery response per application_state_spec.yaml Section 3:
     * application: {application_id, state, created_at, trial_credit_consumed}
     * job: full job record
     * cv: full cv record (or null if not selected)
     * gap_analysis: {questions: [], responses: []} (null if not generated)
     * artifacts: {vpr: {status, artifact_id}, cv_tailored: ..., ...}
   - Returns 200 with response, 404 if not found, 403 if wrong user

2. Register in API Gateway CDK: add GET /applications/{application_id} route

3. Create: src/backend/tests/unit/test_l3_application_recovery.py
   - test_recovery_returns_200_for_own_application
   - test_recovery_returns_403_for_wrong_user
   - test_recovery_returns_404_for_missing_application
   - test_recovery_response_contains_all_required_fields
   - test_recovery_null_gap_questions_when_in_created_state
   - test_recovery_populated_artifacts_when_completed

PROHIBITED:
- DO NOT return data from other users' applications
- DO NOT skip ownership check
- DO NOT read user_id from anywhere except Cognito claims

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l3_application_recovery.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/handlers/application_handler.py
- [ ] Run: cd src/backend && uv run mypy careervp/handlers/application_handler.py --strict
- [ ] Manual: curl GET /applications/{id} with valid token → 200 with full state

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L3_2_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_application_state.py` (TestApplicationRecovery class)
**PAYLOAD:** `docs/refactor/payloads/beta_l3_application_state_test.json` (key: `L3_2_recovery_endpoint`)

---

### Step L3.3: Wire Trial Credit Charging at Gap Question Generation

**Duration:** 1 hour
**Invariant(s) Satisfied:** I5 (credit charge wired), I6 (state transition)

**READ FIRST:**
- `@spec docs/best_practices/yaml/trial_enforcement_spec.yaml`
- `@spec docs/best_practices/yaml/application_state_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: Backend Engineer specializing in transactional workflows and AWS Lambda

CONTEXT:
- Trial credit must be atomically charged BEFORE the LLM call in gap question generation
- Application state must transition to gap_questions_pending at the same time
- This is the enforcement point per trial_enforcement_spec.yaml Section 2.2

TASK: Wire trial credit consume_credit() call into gap_handler before LLM invocation

IMPLEMENTATION DETAILS:

1. Create: src/backend/careervp/logic/trial_service.py
   - Class: TrialService(dal: DynamoDalHandler)
   - check_trial_status(user_id) -> TrialStatus
   - consume_credit(user_id) -> None (raises on limit/expiry)
   - get_usage(user_id) -> TrialUsage (for /users/me/usage endpoint)
   - Implements atomic counter per trial_enforcement_spec.yaml Section 2.1

2. Modify: src/backend/careervp/handlers/gap_handler.py (POST gap-questions route)
   Order of operations:
   1. extract_user_id from Cognito claims
   2. trial_service.check_trial_status(user_id) → raises on expired
   3. trial_service.consume_credit(user_id) → raises on exhausted (atomic)
   4. application_repo.update_state(app_id, user_id, "gap_questions_pending", "cv_selected")
   5. call gap_analysis.generate_questions(cv, job)
   6. persist questions to DynamoDB
   7. application_repo.update_state(app_id, user_id, "gap_questions_ready", "gap_questions_pending")

3. Create: src/backend/tests/unit/test_l3_trial_credit_charging.py
   - test_credit_charged_before_llm_called: mock order verification
   - test_trial_exhausted_before_llm_call: exhaust → LLM never called
   - test_application_state_transitions_to_pending: state = gap_questions_pending after charge
   - test_application_state_transitions_to_ready: state = gap_questions_ready after LLM

PROHIBITED:
- DO NOT call LLM before charging credit
- DO NOT charge credit after LLM call fails (idempotency issue)
- DO NOT skip application state transition

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l3_trial_credit_charging.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/logic/trial_service.py
- [ ] Run: cd src/backend && uv run mypy careervp/logic/trial_service.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L3_3_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_trial_enforcement.py` (TestTrialIntegration), `test_l3_trial_credit_charging.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l3_application_state_test.json` (key: `L3_3_trial_credit_charging`)

---

### Step L3.4: Test State Recovery on Page Reload

**Duration:** 1 hour
**Invariant(s) Satisfied:** I6

**READ FIRST:**
- `@spec docs/best_practices/yaml/application_state_spec.yaml`
- `@spec docs/best_practices/yaml/testing_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: QA Engineer specializing in stateful workflow testing

CONTEXT:
- With ApplicationRepository and GET /applications/{id} implemented,
  verify that page reload at each of the 7 workflow steps restores correct state

TASK: Implement state recovery test suite validating I6

IMPLEMENTATION DETAILS:

1. Implement (un-RED-phase) src/backend/tests/unit/test_application_state.py
   - TestReloadRecovery class: all parametrized test cases implemented
   - For each state: create record in that state → call GET /applications/{id}
     → assert response contains the data needed to restore that step

2. Create: src/backend/tests/unit/test_l3_state_recovery.py
   - test_created_state_recovery: response has application, no cv, no questions, no artifacts
   - test_gap_questions_ready_recovery: response has questions populated
   - test_artifacts_generating_recovery: response has artifact_statuses with mix of statuses
   - test_artifacts_completed_recovery: all 5 artifacts completed
   - test_trial_credit_not_double_charged_on_reload: reload during pending does not re-charge

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_application_state.py tests/unit/test_l3_state_recovery.py -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/
- [ ] Run: cd src/backend && uv run mypy careervp/ --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L3_4_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_application_state.py`, `src/backend/tests/unit/test_l3_state_recovery.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l3_application_state_test.json` (key: `L3_4_state_recovery`)

---

### Phase 4 Integration Test

**Description:** Simulate workflow interruption, reload page, verify state restored at each of 7 steps

**Pass criterion:** 7/7 workflow steps restore correct state on page reload

---

---

# Phase 5: Trial Enforcement (Layer 5)

**Purpose:** Implement 14-day / 3-application trial limit with race-condition-safe atomic counter
**Invariant:** I5
**Spec:** `docs/best_practices/yaml/trial_enforcement_spec.yaml`

---

### Step L5.1: Implement Trial Expiry Check Middleware

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I5 (partial — expiry check)

**READ FIRST:**
- `@spec docs/best_practices/yaml/trial_enforcement_spec.yaml`
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in subscription enforcement and AWS Lambda

CONTEXT:
- Trial enforcement does not exist yet — any user can create unlimited applications
- Target: 14-day trial limit enforced at every protected route (not just gap-questions)

TASK: Implement trial expiry check in TrialService and wire into handlers

IMPLEMENTATION DETAILS:

1. Implement trial_service.check_trial_status() in src/backend/careervp/logic/trial_service.py
   (created as skeleton in L3.3 — implement the body now)
   - Fetch: dal.get_item(pk=f"USER#{user_id}", sk="TRIAL")
   - Compute: days_elapsed = (now - created_at).days
   - If days_elapsed >= 14: raise TrialExpiredException(user_id)
   - Return: TrialStatus(state="ACTIVE", days_remaining=14-days, credits_remaining=3-count)

2. Add trial check to gap_handler, job_handler (application creation point)
   - Call check_trial_status() before processing
   - Catch TrialExpiredException → return 403 {"error": "trial_expired", ...}

3. Create custom exceptions: src/backend/careervp/models/exceptions.py
   - TrialExpiredException(user_id: str, days_elapsed: int)
   - TrialExhaustedException(user_id: str, application_count: int)

4. Implement (un-RED) tests in test_trial_enforcement.py (TestTrialExpiry class):
   - All 6 test cases implemented with real TrialService mock

PROHIBITED:
- DO NOT compute trial expiry based on application count (only time-based)
- DO NOT skip trial check on any protected application-creation route

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_trial_enforcement.py::TestTrialExpiry -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/logic/trial_service.py
- [ ] Run: cd src/backend && uv run mypy careervp/logic/trial_service.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L5_1_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_trial_enforcement.py` (TestTrialExpiry)
**PAYLOAD:** `docs/refactor/payloads/beta_l5_trial_enforcement_test.json` (key: `L5_1_trial_expiry`)

---

### Step L5.2: Implement 3-Application Counter with Atomic Safety

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I5 (atomic counter, race condition safe)

**READ FIRST:**
- `@spec docs/best_practices/yaml/trial_enforcement_spec.yaml`
- `@spec docs/best_practices/yaml/dynamodb_modeling_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Backend Engineer specializing in DynamoDB atomic operations

CONTEXT:
- Application counter must use DynamoDB ConditionExpression to prevent race conditions
- 5 concurrent requests at count=2 (one below limit) must result in exactly 1 success
- This is a critical safety requirement per trial_enforcement_spec.yaml Section 2.3

TASK: Implement consume_credit() with DynamoDB atomic counter and race condition safety

IMPLEMENTATION DETAILS:

1. Implement trial_service.consume_credit() in src/backend/careervp/logic/trial_service.py
   - Use: DynamoDB.update_item with ConditionExpression:
     UpdateExpression: "SET application_count = application_count + :inc"
     ConditionExpression: "application_count < :max AND trial_active = :true"
     ExpressionAttributeValues: {":inc": 1, ":max": 3, ":true": True}
   - Catch: ConditionalCheckFailedException → raise TrialExhaustedException

2. Create TRIAL record on user registration:
   - Modify auth_handler.register to create TRIAL record with:
     pk=USER#{user_id}, sk=TRIAL, application_count=0, trial_active=True, created_at=now

3. Implement (un-RED) TestApplicationCounter tests in test_trial_enforcement.py:
   - test_first_application_increments_to_1
   - test_third_application_increments_to_3
   - test_fourth_application_raises_trial_exhausted
   - test_uses_dynamodb_condition_expression
   - test_concurrent_requests_exactly_one_succeeds: Use mocking of ConditionalCheckFailedException

PROHIBITED:
- DO NOT use read-modify-write (race condition)
- DO NOT allow count to exceed 3
- DO NOT create TRIAL record outside of user registration

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_trial_enforcement.py::TestApplicationCounter -v --tb=short
- [ ] Run: cd src/backend && uv run mypy careervp/logic/trial_service.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L5_2_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_trial_enforcement.py` (TestApplicationCounter)
**PAYLOAD:** `docs/refactor/payloads/beta_l5_trial_enforcement_test.json` (key: `L5_2_app_counter`)

---

### Step L5.3: Create GET /users/me/usage Endpoint

**Duration:** 1 hour
**Invariant(s) Satisfied:** I5 (usage visibility)

**READ FIRST:**
- `@spec docs/best_practices/yaml/trial_enforcement_spec.yaml`
- `@spec docs/best_practices/yaml/lambda_handler_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: Backend Engineer specializing in REST API design

CONTEXT:
- Users need to see their trial status: days remaining, applications used/remaining

TASK: Add GET /users/me/usage route to user_handler.py

IMPLEMENTATION DETAILS:

1. Modify: src/backend/careervp/handlers/user_handler.py
   - Add route: GET /users/me/usage
   - Extract: user_id from Cognito claims
   - Call: trial_service.get_usage(user_id) → TrialUsage
   - Return 200 with schema from trial_enforcement_spec.yaml Section 4.1

2. Implement TrialService.get_usage():
   - Fetch TRIAL record from DynamoDB
   - Calculate days_elapsed, days_remaining, credits_remaining
   - Return TrialUsage Pydantic model

3. Register route in CDK api_construct.py: GET /users/me/usage

4. Implement (un-RED) TestUsageEndpoint tests in test_trial_enforcement.py

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_trial_enforcement.py::TestUsageEndpoint -v --tb=short
- [ ] Run: cd src/backend && uv run ruff check careervp/handlers/user_handler.py
- [ ] Run: cd src/backend && uv run mypy careervp/handlers/user_handler.py --strict

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L5_3_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_trial_enforcement.py` (TestUsageEndpoint)
**PAYLOAD:** `docs/refactor/payloads/beta_l5_trial_enforcement_test.json` (key: `L5_3_usage_endpoint`)

---

### Step L5.4: Integration Test Trial Enforcement

**Duration:** 1 hour
**Invariant(s) Satisfied:** I5 (all 3 sub-tests)

**READ FIRST:**
- `@spec docs/best_practices/yaml/trial_enforcement_spec.yaml`
- `@spec docs/best_practices/yaml/testing_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: QA Engineer specializing in integration testing and concurrency

TASK: Implement full trial enforcement integration test suite

IMPLEMENTATION DETAILS:

1. Implement TestTrialIntegration in test_trial_enforcement.py:
   - test_exhaust_3_applications_block_4th: full flow with mock DynamoDB
   - test_day_15_user_blocked_on_any_route: mock created_at 15 days ago
   - test_concurrent_boundary_no_overcount: 5 concurrent mocked requests, verify count

2. Generate evidence: docs/beta/evidence/I5_trial/trial-enforcement-report.json
   Format per BETA_STRUCTURED_OUTLINE Section 5.1:
   {"test_name": "exhaust_3_apps", "expected_outcome": "403_trial_exhausted", "actual_outcome": "403_trial_exhausted", "pass": true}

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_trial_enforcement.py -v --tb=short
- [ ] Evidence: docs/beta/evidence/I5_trial/trial-enforcement-report.json exists and all pass=true

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L5_4_results.md
- Write evidence: docs/beta/evidence/I5_trial/trial-enforcement-report.json
"""
```

**TEST:** `src/backend/tests/unit/test_trial_enforcement.py` (full)
**PAYLOAD:** `docs/refactor/payloads/beta_l5_trial_enforcement_test.json` (key: `L5_4_trial_integration`)

---

### Phase 5 Integration Test

**Description:** Exhaust 3 apps → block 4th. Simulate day-15 → block. 5 concurrent at boundary → exactly 1 succeeds.

**Evidence:** `docs/beta/evidence/I5_trial/trial-enforcement-report.json`

---

---

# Phase 6: Route Surface Cleanup (Layer 5)

**Purpose:** Single canonical route per operation; remove all duplicate `/api/*` shadow routes
**Invariant:** I7

---

### Step L6.1: Document Canonical Route Decisions

**Duration:** 30 minutes
**Invariant(s) Satisfied:** I7 (route spec frozen)
**Status:** ✅ Completed (2026-02-27, operator gate PASS on `beta/exec-runbook6`)
**Execution Result:** `docs/beta/execution_results/L6_1_results.md`

**READ FIRST:**
- `@spec docs/refactor/specs/api_contract_spec.yaml`
- `@ref docs/beta/STRICT_CHECKLIST_MAPPED_TO_SWAGGER.md`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: API Architect specializing in REST API design

TASK: Create canonical route decision document from STRICT_CHECKLIST and Swagger

IMPLEMENTATION DETAILS:

1. Read: docs/beta/STRICT_CHECKLIST_MAPPED_TO_SWAGGER.md
2. Read: current Swagger JSON for deployed routes
3. Create: docs/beta/canonical_routes.md
   - For each operation: chosen path, deprecated paths to remove, rationale
   - Source the 30 canonical routes from beta_l6_route_surface_test.json

VALIDATION CRITERIA:
- [ ] docs/beta/canonical_routes.md exists with all 30 routes documented

OUTPUT FORMAT:
- Write: docs/beta/canonical_routes.md
- Write results to: docs/beta/execution_results/L6_1_results.md
"""
```

**TEST:** None (documentation step)
**PAYLOAD:** `docs/refactor/payloads/beta_l6_route_surface_test.json`

---

### Step L6.2: Remove Duplicate API Gateway Routes

**Duration:** 2 hours
**Invariant(s) Satisfied:** I7
**Status:** ⛔ Blocked (2026-02-27, `cdk diff` requires AWS credentials not available in current environment)
**Execution Result:** `docs/beta/execution_results/L6_2_results.md`

**READ FIRST:**
- `@spec docs/best_practices/yaml/cicd_spec.yaml`
- `@spec docs/refactor/specs/api_contract_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior AWS CDK Engineer specializing in API Gateway route management

CONTEXT:
- Current state: duplicate routes exist (/api/cv AND /users/me/cv for same operation)
  Source: Swagger JSON shows both sets active
- Target state: exactly 30 canonical routes, zero /api/* duplicates
- Risk: additive migration — do NOT remove routes until new routes tested

TASK: Remove deprecated /api/* duplicate routes from CDK api_construct.py

IMPLEMENTATION DETAILS:

1. Read: infra/careervp/api_construct.py (all current route definitions)
2. Identify: any route using /api/ prefix or duplicating canonical routes
3. Remove: duplicate route.add_method() calls for deprecated paths
4. Keep: canonical routes from docs/beta/canonical_routes.md
5. CDK diff before deploy: verify only route deletions, no unintended changes

6. Create: src/backend/tests/unit/test_l6_route_dedup.py
   - test_no_api_prefix_routes_in_cdk: grep api_construct.py for /api/ prefix → 0
   - test_canonical_route_count: count add_method calls matches expected 30

PROHIBITED:
- DO NOT remove routes before verifying canonical equivalent is tested
- DO NOT change method implementations — route definitions only

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] grep -n '"/api/' infra/careervp/api_construct.py | wc -l → 0
- [ ] Run: cd infra && uv run cdk synth --app='python app.py' (must succeed)
- [ ] Run: cd src/backend && uv run pytest tests/unit/test_l6_route_dedup.py -v
- [ ] Run: cd infra && uv run cdk diff (verify only deletions, nothing unexpected)

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L6_2_results.md
"""
```

**TEST:** `src/backend/tests/unit/test_l6_route_dedup.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l6_route_surface_test.json` (key: `L6_2_route_dedup`)

---

### Step L6.3: Update Swagger Contract

**Duration:** 30 minutes
**Invariant(s) Satisfied:** I7 (contract frozen)
**Status:** ⛔ Blocked (2026-02-27, staging OpenAPI export unavailable due network/AWS endpoint access)
**Execution Result:** `docs/beta/execution_results/L6_3_results.md`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: API Documentation Engineer

TASK: Regenerate Swagger/OpenAPI spec from deployed API Gateway and freeze as canonical contract

IMPLEMENTATION DETAILS:

1. Run: python src/backend/generate_openapi.py > docs/swagger/careervp-api-staging-v1.json
2. Verify: spec contains exactly the 30 canonical routes (no /api/* paths)
3. Freeze: commit spec as the reference for I7 evidence

VALIDATION CRITERIA:
- [ ] docs/swagger/careervp-api-staging-v1.json exists
- [ ] jq '[.paths | keys[]]' spec.json | wc -l → 30

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L6_3_results.md
"""
```

**TEST:** None (documentation step)
**PAYLOAD:** `docs/refactor/payloads/beta_l6_route_surface_test.json`

---

### Step L6.4: Verify Route Surface Matches Spec

**Duration:** 30 minutes
**Invariant(s) Satisfied:** I7
**Status:** ✅ Completed (2026-02-27, operator gate PASS on `beta/exec-runbook6`)
**Execution Result:** `docs/beta/execution_results/L6_4_results.md`

**PROMPT:**
```bash
# VSCode + Anthropic Haiku
"""
ROLE: QA Engineer specializing in API contract testing

TASK: Compare deployed API Gateway routes against frozen spec, generate I7 evidence

IMPLEMENTATION DETAILS:

1. Run: aws apigateway get-resources --rest-api-id $API_ID --region $REGION
2. Extract deployed paths and methods
3. Diff against docs/beta/canonical_routes.md (or frozen spec)
4. Assert: diff output is empty (no extra routes, no missing routes)

5. Generate: docs/beta/evidence/I7_routes/route-surface-diff.txt
6. Generate: docs/beta/evidence/I7_routes/frozen_spec.json (deployed route list)

VALIDATION CRITERIA:
- [ ] diff output is empty
- [ ] docs/beta/evidence/I7_routes/route-surface-diff.txt exists and is empty

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L6_4_results.md
- Write evidence: docs/beta/evidence/I7_routes/route-surface-diff.txt
"""
```

**TEST:** `src/backend/tests/unit/test_l6_route_surface.py`
**PAYLOAD:** `docs/refactor/payloads/beta_l6_route_surface_test.json` (key: `L6_4_route_surface`)

---

### Phase 6 Integration Test

**Description:** Compare deployed routes to frozen spec, assert exact match

**Evidence:** `docs/beta/evidence/I7_routes/route-surface-diff.txt`

**Pass criterion:** Empty diff output

---

---

# Phase 7 [FE]: Frontend Integration (Layer 6)

**Purpose:** Complete user workflow with page reload recovery at every step
**Invariant:** I6

---

### Step L7.1 [FE]: Implement Cognito Auth Flow

**Duration:** 2 hours
**Invariant(s) Satisfied:** I3 (frontend sends valid JWT)

**READ FIRST:**
- `@spec docs/best_practices/yaml/cognito_spec.yaml`
- `@spec docs/best_practices/yaml/frontend_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Frontend Engineer specializing in React, TypeScript, Next.js, and AWS Cognito

CONTEXT: Cognito deployed (L2.1), API Gateway authorizer active (L2.2)

TASK: Implement complete Cognito auth flow: register, login, refresh, protected routes

IMPLEMENTATION DETAILS:

1. Implement: src/frontend/src/pages/auth/register.tsx
   - Form: email, password, name
   - On submit: authService.signUp() → show "check email for verification"
   - Error handling: email already exists, password too weak

2. Implement: src/frontend/src/pages/auth/login.tsx
   - Form: email, password
   - On submit: authService.signIn() → redirect to /dashboard
   - Error handling: wrong credentials, unverified email

3. Implement: src/frontend/src/auth/ProtectedRoute.tsx
   - HOC: checks isAuthenticated → redirects to /login if false
   - Shows loading state during auth check

4. Implement: src/frontend/src/api/apiClient.ts (if not done in L2.4)
   - Axios interceptor adds Authorization: Bearer {token}
   - Auto-refresh on 401

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] npm run build (zero TypeScript errors)
- [ ] npm test (all auth unit tests pass)
- [ ] Manual: register → verify email → login → /dashboard visible
- [ ] Manual: /dashboard without login → redirect to /login

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L7_1_results.md
"""
```

**TEST:** `src/frontend/src/auth/__tests__/authService.test.ts`
**PAYLOAD:** `docs/refactor/payloads/beta_l2_auth_scenarios_test.json`

---

### Step L7.2 [FE]: Implement CV Upload Workflow

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I6 (step: cv_selected state)

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Frontend Engineer specializing in file upload and React

TASK: Implement CV upload page with file selection, upload progress, and state persistence

IMPLEMENTATION DETAILS:

1. Implement: src/frontend/src/pages/cv/upload.tsx
   - File input (PDF only, max 10MB)
   - Upload via POST /users/me/cv with multipart/form-data
   - Progress indicator during upload
   - On success: store cv_id in session, redirect to job creation

2. Implement: src/frontend/src/pages/cv/select.tsx (if multiple CVs)
   - List CVs via GET /users/me/cv
   - Select existing or upload new

3. On page reload in cv_selected state:
   - GET /applications/{id} → application.cv.cv_id present
   - Restore: show CV selected, enable "continue" button

VALIDATION CRITERIA:
- [ ] npm run build (zero TypeScript errors)
- [ ] Manual: upload PDF → cv_id visible in network response
- [ ] Manual: reload page → CV still selected (state restored)

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L7_2_results.md
"""
```

**TEST:** `src/frontend/src/pages/cv/__tests__/upload.test.tsx`

---

### Step L7.3 [FE]: Implement Job Application Workflow

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I6 (steps: created, gap_questions states)

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Frontend Engineer

TASK: Implement job creation form, gap question display, and gap response submission

IMPLEMENTATION DETAILS:

1. Implement: src/frontend/src/pages/application/create.tsx
   - Form: job title, company, job description
   - POST /jobs → creates job + application
   - Store: application_id in session

2. Implement: src/frontend/src/pages/application/gap-questions.tsx
   - Load: GET /jobs/{job_id}/gap-questions
   - Display: 10 questions grouped by tag category
   - Submit: POST /jobs/{job_id}/gap-responses (all 10 answers)
   - On submit: redirect to artifact generation

3. State recovery on reload:
   - GET /applications/{id} → if gap_questions_ready: show questions form
   - Pre-populate form with any saved draft responses

VALIDATION CRITERIA:
- [ ] npm run build
- [ ] Manual: create job → see 10 AI questions → submit responses

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L7_3_results.md
"""
```

---

### Step L7.4 [FE]: Implement Artifact Polling

**Duration:** 1.5 hours
**Invariant(s) Satisfied:** I8 (polling confirms status transitions)

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Frontend Engineer specializing in async polling patterns

TASK: Implement useArtifactPolling hook for all 5 artifact types

IMPLEMENTATION DETAILS:

1. Create: src/frontend/src/hooks/useArtifactPolling.ts
   - Polls GET /{artifact_type}/{job_id}/status every 3 seconds
   - Returns: {status, artifact_id, content_url, error}
   - Stops polling when status = "completed" or "failed"
   - Exponential backoff on repeated failures

2. Implement: src/frontend/src/pages/application/results.tsx
   - Shows 5 artifact cards, each with polling status (pending/processing/completed)
   - On completed: show download link / view content
   - On failed: show retry button (future feature — show error for now)

3. State recovery on reload in artifacts_generating state:
   - GET /applications/{id} → artifact_statuses shows current progress
   - Resume polling for any still-pending artifacts

VALIDATION CRITERIA:
- [ ] Manual: submit gap responses → see 5 artifact cards updating in real-time
- [ ] Manual: reload page mid-generation → polling resumes correctly

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L7_4_results.md
"""
```

---

### Step L7.5 [FE]: Implement State Recovery on Reload

**Duration:** 1 hour
**Invariant(s) Satisfied:** I6 (all 7 steps)

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior Frontend Engineer specializing in React state management

TASK: Implement useApplicationState hook for full page-reload recovery

IMPLEMENTATION DETAILS:

1. Create: src/frontend/src/hooks/useApplicationState.ts
   - On mount: GET /applications/{id} from localStorage/URL param
   - Maps state to correct page: per application_state_spec.yaml Section 1
   - Returns: {application, job, cv, gapAnalysis, artifacts, currentStep}

2. Implement router: src/frontend/src/app/ApplicationRouter.tsx
   - Based on application.state → render correct step component
   - Handles all 7 states including failed states

3. Verify I6: manually test reload at each of 7 workflow steps

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] npm run build (zero TypeScript errors)
- [ ] Manual test at each of 7 workflow steps:
  - [ ] created: reload → CV selection step shown
  - [ ] cv_selected: reload → job creation step shown
  - [ ] gap_questions_pending: reload → loading spinner (questions generating)
  - [ ] gap_questions_ready: reload → question form shown with questions
  - [ ] gap_responses_submitted: reload → generating artifacts view
  - [ ] artifacts_generating: reload → artifact progress cards
  - [ ] artifacts_completed: reload → all artifacts shown

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L7_5_results.md
- Generate: docs/beta/evidence/I6_state/state-recovery-matrix.json
"""
```

**TEST:** E2E tests (Playwright): `src/frontend/e2e/state-recovery.spec.ts`
**PAYLOAD:** `docs/refactor/payloads/beta_l3_application_state_test.json` (reload_scenarios)

---

### Phase 7 [FE] Integration Test

**Description:** Full E2E workflow with page reloads at each of 7 steps

**Evidence:** `docs/beta/evidence/I6_state/state-recovery-matrix.json`

**Pass criterion:** 7/7 steps restore correct state on reload

---

---

# Phase 8: Operational Readiness (Layer 7)

**Purpose:** Deploy to staging, run smoke tests, generate all 8 evidence artifacts, sign-off
**Invariants:** All (I1–I8)

---

### Step L8.1: Deploy CDK to Staging

**Duration:** 1 hour
**Invariant(s) Satisfied:** All (staging infrastructure)

**READ FIRST:**
- `@spec docs/best_practices/yaml/cicd_spec.yaml`
- `@spec docs/refactor/specs/deployment_spec.yaml`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Senior DevOps Engineer specializing in AWS CDK and CI/CD deployment

CONTEXT: All layers L0–L6 complete. Deploy to stage.careervp.com.

TASK: Deploy CDK stack to staging environment, configure custom domain, validate

IMPLEMENTATION DETAILS:

1. Pre-deploy validation:
   cd infra && uv run cdk synth --app='python app.py' --require-approval never
   cd infra && uv run cdk diff CareervpStack-staging

2. Deploy:
   cd infra && uv run cdk deploy CareervpStack-staging --require-approval never

3. Post-deploy:
   - Verify custom domain: stage.careervp.com resolves
   - Verify TLS 1.2: curl -v https://stage.careervp.com/health
   - Run health check: curl https://stage.careervp.com/health → 200

4. CDK outputs to capture:
   - API Gateway URL
   - Cognito User Pool ID
   - Cognito Client ID
   - CloudFront distribution URL (if applicable)

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] cdk deploy exits 0
- [ ] curl https://stage.careervp.com/health → {"status": "healthy", "services": {...}}
- [ ] TLS: openssl s_client -connect stage.careervp.com:443 shows TLSv1.2 or higher
- [ ] Cognito User Pool visible in AWS Console staging region

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L8_1_results.md
- Include: CDK output table, health check response, TLS verification output
"""
```

---

### Step L8.2: Run Smoke Tests Against Staging

**Duration:** 1 hour
**Invariant(s) Satisfied:** All (partial validation)

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: QA Engineer specializing in smoke testing and API validation

CONTEXT: Staging deployed at https://stage.careervp.com

TASK: Run smoke test suite against staging — validate all critical paths

IMPLEMENTATION DETAILS:

1. Run existing smoke tests:
   cd src/backend && bash tests/aws_cli_smoke.sh (if applicable to staging)
   cd src/backend && uv run pytest tests/e2e/ -v -m e2e --tb=short

2. Manual smoke test workflow:
   a. Register new user via POST /auth/register → verify email in Cognito
   b. Login → receive JWT tokens
   c. Upload CV → assert 200 and cv_id returned
   d. Create job → assert 200 and job_id returned
   e. Generate gap questions → assert 200 and 10 AI questions (not templates)
   f. Submit gap responses → assert 200
   g. Poll VPR status → assert completed within 90 seconds
   h. GET /vprs → assert non-empty array with generated VPR

3. Template detection scan:
   Run all generators 3 times, scan output for TEMPLATE_PATTERNS from payload file

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] Full workflow smoke test passes end-to-end
- [ ] 0 template pattern matches in generator outputs
- [ ] VPR generation completes within 90 seconds
- [ ] GET /vprs returns non-empty array

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L8_2_results.md
- Include: smoke test log output
"""
```

---

### Step L8.3: Generate Evidence Bundle (E1–E8)

**Duration:** 2 hours
**Invariant(s) Satisfied:** All (evidence generation)

**READ FIRST:**
- `@ref docs/beta/BETA_STRUCTURED_OUTLINE_2026-03-11.md#section-5`

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: QA Engineer specializing in automated evidence generation

CONTEXT: All invariant tests must be run against staging and evidence saved
per BETA_STRUCTURED_OUTLINE_2026-03-11.md Section 5.1

TASK: Generate all 8 evidence artifacts by running invariant tests against staging

IMPLEMENTATION DETAILS:

1. E1 — generator-output-audit.json (proves I1):
   Run 50 iterations of each generator, scan for TEMPLATE_PATTERNS
   Format: {generator, run_id, is_template, template_match, response_excerpt}
   Save: docs/beta/evidence/I1_generators/generator-output-audit.json

2. E2 — persistence-roundtrip-report.json (proves I2):
   For each artifact type: generate → poll complete → list → assert ID present. 50 runs.
   Format: {artifact_type, run_id, generated_id, list_contains_id, list_response_length}
   Save: docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json

3. E3 — auth-abuse-matrix.json (proves I3):
   For each protected route, test all 4 auth scenarios
   Format: {route, method, scenario, expected_status, actual_status, pass}
   Save: docs/beta/evidence/I3_auth/auth-abuse-matrix.json

4. E4 — identity-extraction-audit.txt (proves I4):
   Run grep patterns against source. Empty output = pass.
   Save: docs/beta/evidence/I4_identity/identity-extraction-audit.txt

5. E5 — trial-enforcement-report.json (proves I5):
   Run 3 trial scenarios against staging
   Format: {test_name, expected_outcome, actual_outcome, pass}
   Save: docs/beta/evidence/I5_trial/trial-enforcement-report.json

6. E6 [FE] — state-recovery-matrix.json (proves I6):
   At each of 7 workflow steps: reload → assert correct state restored
   Format: {step_name, pre_reload_state, post_reload_state, data_preserved, pass}
   Save: docs/beta/evidence/I6_state/state-recovery-matrix.json

7. E7 — route-surface-diff.txt (proves I7):
   Diff deployed routes vs frozen spec. Empty = pass.
   Save: docs/beta/evidence/I7_routes/route-surface-diff.txt

8. E8 — async-sla-report.json (proves I8):
   50 timing runs for all async operations; p50/p95/p99 latencies
   Format: {operation, run_id, status_transitions, total_ms, sla_met}
   Save: docs/beta/evidence/I8_sla/async-sla-report.json

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] All 8 evidence files exist in docs/beta/evidence/
- [ ] All evidence files contain valid JSON (or text for E4, E7)
- [ ] Evidence age < 24 hours (generated now against HEAD commit)
- [ ] I1: 0 template matches in E1
- [ ] I2: all list_contains_id=true in E2
- [ ] I3: all pass=true in E3
- [ ] I4: E4 file is empty
- [ ] I5: all pass=true in E5
- [ ] I6: 7/7 pass=true in E6
- [ ] I7: E7 file is empty
- [ ] I8: all sla_met=true in E8

OUTPUT FORMAT:
- Write results to: docs/beta/execution_results/L8_3_results.md
- All 8 evidence files written to docs/beta/evidence/
"""
```

---

### Step L8.4: Run Final Sign-Off Checklist

**Duration:** 30 minutes

**PROMPT:**
```bash
# VSCode + Anthropic Sonnet
"""
ROLE: Engineering Lead conducting beta launch sign-off

TASK: Run final sign-off checklist per BETA_STRUCTURED_OUTLINE Section 5 and generate sign-off document

IMPLEMENTATION DETAILS:

1. Verify all 8 evidence artifacts are fresh (< 24 hours old):
   ls -la docs/beta/evidence/*/

2. For each invariant I1–I8:
   - Verify evidence file exists
   - Verify pass criterion met (0 template matches, all pass=true, empty diff, etc.)
   - Record: PASS or FAIL with specific evidence line

3. Generate: docs/beta/sign_off.md with:
   - Timestamp of sign-off
   - Commit SHA of deployed HEAD
   - Per-invariant: PASS/FAIL with evidence reference
   - Overall: GO or NO-GO decision

VALIDATION CRITERIA (ALL MUST PASS):
- [ ] All 8 invariants marked PASS
- [ ] docs/beta/sign_off.md exists with GO decision
- [ ] Evidence age < 24 hours

OUTPUT FORMAT:
- Write: docs/beta/sign_off.md
- Write results to: docs/beta/execution_results/L8_4_results.md
"""
```

---

### Phase 8 Live Test Suite

Execute against deployed staging, measure SLAs, generate all evidence JSON:

```bash
# Run all invariant tests against staging
export STAGING_API_URL="https://stage.careervp.com"
cd src/backend && uv run pytest tests/e2e/ -v -m e2e --tb=short

# Generate evidence bundle
python scripts/generate_evidence_bundle.py --env staging --runs 50
```

---

---

# Phase Completion Checklist

| Phase | Layer | Steps | Integration Test | Evidence | Status |
|-------|-------|-------|------------------|----------|--------|
| Phase 1: Generator Reality | L0 | L0.1–L0.5 | ✓ test_l0_phase_integration.py | E1 | ✅ Completed (L0.1–L0.5 + integration + E1 evidence) |
| Phase 2: Persistence | L1 | L1.1–L1.4 | ✓ test_l1_phase_integration.py | E2 | ✅ Completed (L1.1–L1.4 + integration + E2 evidence) |
| Phase 3: Auth Migration | L2 | L2.1–L2.5 | ✓ test_l2_auth_integration.py | E3, E4 | 🟡 In progress (L2.1–L2.3 + L2.5 complete; L2.4 [FE] blocked: no frontend workspace) |
| Phase 4: Application State | L3 | L3.1–L3.4 | ✓ test_l3_state_recovery.py | E6 (partial, [FE]) | ⬜ |
| Phase 5: Trial Enforcement | L5 | L5.1–L5.4 | ✓ test_l5_trial_integration.py | E5 | ⬜ |
| Phase 6: Route Cleanup | L6 | L6.1–L6.4 | ✓ route surface diff | E7 | 🟡 In progress (L6.1 + L6.4 complete; L6.2 + L6.3 blocked on AWS access for diff/openapi export) |
| Phase 7: Frontend | L7 | L7.1–L7.5 [FE] | ✓ Playwright E2E | E6 [FE] | ⛔ Deferred (frontend workspace not available) |
| Phase 8: Operational Readiness | L8 | L8.1–L8.4 | ✓ staging smoke tests | E1–E8 | ⬜ |

---

# Claude Code Audit Snapshot (2026-02-27)

This section records the Claude Code implementation audit summary provided in-session.
Use it as a historical implementation-confidence view (implemented vs scaffolded), not as a replacement for current branch verification.

## Actually Implemented (Production Code Changes)

| Step | Audit Finding |
|------|---------------|
| L1.2 | CVTable removed from handlers; DynamoDalHandler used exclusively (`0` CVTable grep matches) |
| L1.3 | Health handler reports `anthropic` + `dynamodb` (no stale `bedrock/lambda`) |
| L1.4 (partial) | `list_tailored_cvs` DAL returns raw dicts with preserved `sk/status`; list path works end-to-end |
| L2.3 (partial) | `auth_utils.py` reads user id from `requestContext.authorizer.jwt.claims.sub` |
| I7 evidence | `docs/beta/evidence/I7_routes/frozen_spec.json` + `docs/beta/evidence/I7_routes/route-surface-diff.txt` generated |

## Test Scaffolding Marked GREEN (Audit Caveat)

Claude audit identified multiple GREEN suites that were primarily scaffold assertions (`assert True`) at audit time:

- L0.1–L0.5 test files
- L1.1 and parts of L1.4
- L3.1–L3.4 test files

Audit conclusion at that time: many test files were structurally complete but did not yet guarantee production behavior.

## Audit-Flagged Stub Modules

- `careervp/logic/trial_service.py` (`TrialService` shell, `NotImplementedError`)
- `careervp/dal/application_repository.py` (repository shell)

## Audit-Flagged Not Started Areas (at snapshot time)

- L0 real LLM fixes (beyond scaffold confidence)
- L2.1–L2.2 Cognito infra/authorizer rollout
- L3 real state machine + repository hardening
- L5 trial enforcement implementation
- L6.1–L6.3 route cleanup/documentation updates
- L7 frontend
- L8 staging deploy/sign-off
- Missing evidence at snapshot time: E1–E6, E8

---

# Evidence Bundle Commands

Run these against staging to generate all 8 evidence artifacts:

```bash
# E1: Generator output audit
python scripts/evidence/generate_e1_generator_audit.py \
  --api-url https://stage.careervp.com \
  --runs 50 \
  --output docs/beta/evidence/I1_generators/generator-output-audit.json

# E2: Persistence roundtrip
python scripts/evidence/generate_e2_persistence_roundtrip.py \
  --api-url https://stage.careervp.com \
  --runs 50 \
  --output docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json

# E3: Auth abuse matrix
python scripts/evidence/generate_e3_auth_matrix.py \
  --api-url https://stage.careervp.com \
  --output docs/beta/evidence/I3_auth/auth-abuse-matrix.json

# E4: Identity extraction audit
grep -rn "X-User-Id\|payload.*user_id\|body.*user_id" \
  src/backend/careervp/handlers/ \
  > docs/beta/evidence/I4_identity/identity-extraction-audit.txt || true
echo "E4 generated. Expected: empty file."

# E5: Trial enforcement
python scripts/evidence/generate_e5_trial_enforcement.py \
  --api-url https://stage.careervp.com \
  --output docs/beta/evidence/I5_trial/trial-enforcement-report.json

# E6 [FE]: State recovery matrix (requires frontend + E2E test runner)
npx playwright test src/frontend/e2e/state-recovery.spec.ts \
  --reporter=json > docs/beta/evidence/I6_state/state-recovery-matrix.json

# E7: Route surface diff
aws apigateway get-resources --rest-api-id $API_ID \
  | python scripts/evidence/extract_routes.py \
  | diff - docs/beta/evidence/I7_routes/frozen_spec.json \
  > docs/beta/evidence/I7_routes/route-surface-diff.txt || true
echo "E7 generated. Expected: empty diff."

# E8: Async SLA report
python scripts/evidence/generate_e8_sla_report.py \
  --api-url https://stage.careervp.com \
  --runs 50 \
  --output docs/beta/evidence/I8_sla/async-sla-report.json
```

---

# Sign-Off Criteria

Per BETA_STRUCTURED_OUTLINE_2026-03-11.md Section 5.2:

| Rule | Requirement |
|------|-------------|
| Maximum evidence age | 24 hours at time of sign-off |
| Evidence environment | Must be `staging` (not `dev` or `local`) |
| Evidence reflects | HEAD commit of deployed stage |
| Re-run trigger | Any deployment to staging after evidence generation |
| Storage location | `docs/beta/evidence/` |

**Launch only if:**
1. All I1–I8 invariants: PASS
2. All evidence files: < 24 hours old
3. Evidence generated against: HEAD commit at `stage.careervp.com`
4. No invariant waived without written rationale in `docs/beta/sign_off.md`
5. Cut trigger check (Day 9 = 2026-03-07): if L0 or L1 incomplete, escalate immediately

---

*Runbook generated: 2026-02-26 | Pattern: docs/refactor/execution_runbook_2.md | Deadline: 2026-03-11*
