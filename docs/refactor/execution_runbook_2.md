# CareerVP Execution Runbook 2.0 - Remaining Tasks

**Document Version:** 2.0
**Date:** 2026-02-17
**Purpose:** Complete implementation of remaining phases following execution_runbook.md format

---

## Implementation Order

1. **Quality Gaps FIRST** (Phases 2-7) - Core business logic
2. **API Contract Gaps SECOND** (Phase 10) - HTTP endpoints

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
- `docs/refactor/specs/cost_optimization_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement CV Summarizer to reduce token costs:

1. Create: src/backend/careervp/logic/cv_summarizer.py
   - Class: CVSummarizer
   - Method: summarize(cv: UserCV) -> dict
   - Extract key sections: summary, experience, skills, education
   - Truncate to max lengths for LLM efficiency

2. Integrate: src/backend/careervp/logic/llm_client.py
   - Import CVSummarizer
   - Use summarization before LLM calls for CV-heavy prompts

3. Create: tests/unit/test_cv_summarizer.py

KNOWLEDGE: docs/refactor/specs/cost_optimization_spec.yaml
"""
```

### Step 2.2: Implement LLM Cache

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement LLM response cache:

1. Create: src/backend/careervp/logic/llm_cache.py
   - Class: LLMResponseCache
   - Use DynamoDB with TTL for caching
   - Cache key: hash of prompt + CV ID

2. Integrate: src/backend/careervp/logic/llm_client.py
   - Check cache before calling Bedrock
   - Store response on cache miss

3. Create: tests/unit/test_llm_cache.py

KNOWLEDGE: docs/refactor/specs/cost_optimization_spec.yaml (caching strategy)
"""
```

### Step 2.3: Wire Circuit Breaker into LLMClient

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Wire circuit breaker into LLMClient:

1. Update: src/backend/careervp/logic/llm_client.py
   - Import CircuitBreaker from handlers/utils
   - Wrap Bedrock calls with circuit breaker
   - Handle open circuit gracefully

2. Verify: tests/unit/test_llm_client.py
   - Add circuit breaker test cases

KNOWLEDGE: docs/refactor/specs/circuit_breaker_spec.yaml
"""
```

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
Refactor vpr_generator.py to 6-stage pipeline per vpr_6stage_spec.yaml:

1. Update: src/backend/careervp/logic/vpr_generator.py
   - Add Stage 1: _analyze_input() -> AnalysisResult
   - Add Stage 2: _extract_evidence() -> EvidenceList
   - Add Stage 3: _synthesize() -> DraftProposition
   - Add Stage 4: _self_correct() -> CorrectedProposition
   - Add Stage 5: _generate_output() -> VPRData
   - Add Stage 6: _final_meta_evaluation() -> FinalVPRData
   - Each stage as separate method with clear inputs/outputs

2. Update: src/backend/careervp/logic/prompts/vpr_prompt.py
   - Add prompt templates for each stage

3. Wire anti-AI detection:
   - Import check_anti_anti_ai_patterns from fvs_validator
   - Call in Stage 6: _final_meta_evaluation()

4. Update: tests/unit/test_vpr_generator.py

KNOWLEDGE: docs/refactor/specs/vpr_6stage_spec.yaml (stages section)
"""
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
Implement 3-step CV tailoring per cv_tailoring_spec.yaml:

1. Update: src/backend/careervp/logic/cv_tailoring.py
   - Step 1: analyze_and_map_keywords() - Extract 12-18 keywords from job
   - Step 2: tailor_cv() - Apply keywords with ATS scoring
   - Step 3: validate_and_finalize() - Final validation

2. Add self-correction loop:
   - If ATS score < 8.0, regenerate with feedback
   - Max 3 iterations

3. Add CAR/STAR enforcement:
   - Validate achievement bullets follow STAR format

4. Update: tests/unit/test_cv_tailoring.py

KNOWLEDGE: docs/refactor/specs/cv_tailoring_spec.yaml
"""
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
Fix gap analysis issues:

1. Update: src/backend/careervp/logic/gap_analysis.py
   - Change question limit from 5 to 10
   - Add question tagging in prompt
   - Tags: [CV IMPACT], [INTERVIEW/MVP ONLY], [TECHNICAL], [BEHAVIORAL]

2. Enhance: src/backend/careervp/handlers/gap_handler.py
   - Add full CRUD operations
   - Add GET endpoints for questions and responses

3. Update: tests/unit/test_gap_analysis.py

KNOWLEDGE: docs/refactor/specs/gap_analysis_spec.yaml
"""
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
Implement full FVS validation per fvs_spec.yaml:

1. Update: src/backend/careervp/logic/fvs_validator.py
   - Grammar validation (min 9.0)
   - Tone validation (min 8.0)
   - Anti-AI pattern detection (min 9.0)
   - Formatting validation (min 8.0)
   - Content structure validation
   - ATS scoring for CV/cover letter
   - Cross-document consistency check

2. Wire anti-AI into all pipelines:
   - VPR: Import and call check_anti_ai_patterns
   - Cover Letter: Import and call check_anti_ai_patterns
   - CV Tailoring: Import and call check_anti_ai_patterns

3. Update: tests/unit/test_fvs_validator.py
   - Add comprehensive FVS tests

4. Create: tests/cover-letter/unit/test_fvs_integration.py
   - Test FVS integration with cover letter

KNOWLEDGE: docs/refactor/specs/fvs_spec.yaml (validation_checks section)
"""
```

---

# PART 2: API CONTRACT GAPS

## Phase 10: API Contract Coverage - 12 Missing Endpoints

**Duration:** 2 days | **Effort:** 10 hours
**Status (2026-02-16):** 12 of 27 endpoints implemented

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `api_contract_spec.yaml` | API endpoints |

### Step 10.1: Implement User Handler (3 endpoints)

**READ FIRST:**
- `docs/refactor/specs/api_contract_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement User endpoints per api_contract_spec.yaml:

1. Create: src/backend/careervp/models/user.py
   - User model with email, name, preferences

2. Create: src/backend/careervp/dal/user_repository.py
   - UserRepository with DynamoDB operations
   - get_user(user_id), update_user(user_id, data)

3. Create: src/backend/careervp/handlers/user_handler.py
   - GET /users/me -> get_current_user()
   - PUT /users/me -> update_current_user()
   - GET /users/me/cvs -> list_user_cvs()

4. Create: tests/unit/test_user_handler.py

Endpoints:
- GET /users/me (operationId: getCurrentUser)
- PUT /users/me (operationId: updateCurrentUser)
- GET /users/me/cvs (operationId: listUserCVs)

KNOWLEDGE: docs/refactor/specs/api_contract_spec.yaml (users section)
"""
```

### Step 10.2: Implement Job Handler (3 endpoints)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Job endpoints per api_contract_spec.yaml:

1. Create: src/backend/careervp/models/job.py
   - Job model with id, title, company, description, status

2. Create: src/backend/careervp/dal/jobs_repository.py
   - JobsRepository with DynamoDB operations
   - create_job(), get_job(), list_jobs(), get_jobs_by_user()

3. Create: src/backend/careervp/handlers/job_handler.py
   - POST /jobs -> create_job()
   - GET /jobs -> list_jobs()
   - GET /jobs/{jobId} -> get_job()

4. Create: tests/unit/test_job_handler.py

Endpoints:
- POST /jobs (operationId: createJob)
- GET /jobs (operationId: listJobs)
- GET /jobs/{jobId} (operationId: getJob)

KNOWLEDGE: docs/refactor/specs/api_contract_spec.yaml (jobs section)
"""
```

### Step 10.3: Add Status Endpoints to Existing Handlers

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Add status/list endpoints to existing handlers:

1. Update: src/backend/careervp/handlers/cv_tailoring_handler.py
   - Add GET /cv-tailoring/{cvTailoringId} -> get_tailored_cv_status()
   - Add GET /users/me/tailored-cvs -> list_tailored_cvs()

2. Update: src/backend/careervp/handlers/cover_letter_handler.py
   - Add GET /cover-letter/{coverLetterId} -> get_cover_letter_status()
   - Add GET /users/me/cover-letters -> list_cover_letters()

3. Update: src/backend/careervp/handlers/interview_prep_handler.py
   - Add GET /interview-prep/{interviewPrepId} -> get_interview_prep_status()

4. Create: tests/unit/test_status_endpoints.py

Endpoints:
- GET /cv-tailoring/{cvTailoringId} (operationId: getTailoredCV)
- GET /users/me/tailored-cvs (operationId: listTailoredCVs)
- GET /cover-letter/{coverLetterId} (operationId: getCoverLetter)
- GET /users/me/cover-letters (operationId: listCoverLetters)
- GET /interview-prep/{interviewPrepId} (operationId: getInterviewPrep)

KNOWLEDGE: docs/refactor/specs/api_contract_spec.yaml (cv-tailoring, cover-letter, interview-prep sections)
"""
```

### Step 10.4: Implement Health Endpoint

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement Health endpoint:

1. Create: src/backend/careervp/handlers/health_handler.py
   - GET /health -> health_check()
   - Return: status, timestamp, version

2. Create: tests/unit/test_health_handler.py

Endpoint:
- GET /health (operationId: healthCheck)

KNOWLEDGE: docs/refactor/specs/api_contract_spec.yaml (health section)
"""
```

---

# PART 3: TEST CREATION

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
"""
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

- [ ] Phase 2: CV Summarizer implemented
- [ ] Phase 2: LLM Cache implemented
- [ ] Phase 2: Circuit breaker wired
- [ ] Phase 3: 6-stage VPR pipeline
- [ ] Phase 3: Anti-AI wired
- [ ] Phase 4: 3-step CV tailoring
- [ ] Phase 4: Self-correction loop (ATS >= 8.0)
- [ ] Phase 5: 10 question limit
- [ ] Phase 5: Question tagging
- [ ] Phase 6: Cover Letter unit tests
- [ ] Phase 6: Cover Letter integration tests
- [ ] Phase 6: Cover Letter E2E tests
- [ ] Phase 7: ATS scoring
- [ ] Phase 7: Anti-AI scoring wired
- [ ] Phase 7: Cross-doc consistency
- [ ] Phase 10: User handler (3 endpoints)
- [ ] Phase 10: Job handler (3 endpoints)
- [ ] Phase 10: Status endpoints (5 endpoints)
- [ ] Phase 10: Health endpoint
- [ ] VPR Async: E2E test
- [ ] All tests passing
- [ ] Lint clean
- [ ] Type check clean
- [ ] CDK synth succeeds
