# Phase 10: Cover Letter Generation - Architect Prompt

**Date:** 2026-02-05
**Phase:** 10 - Cover Letter Generation
**Architect Role:** Design, document, test, and hand off (NO implementation)
**Engineer Role:** Implement code following Architect's specifications

---

## 🎯 MISSION: PHASE 10 COVER LETTER GENERATION (STRICT TDD & ARCHITECTURAL RIGOR)

Act as **Lead Architect**. Your responsibility is to create **COMPLETE** architectural documentation for Phase 10: Cover Letter Generation following the **5-Gate TDD Methodology** established in Phase 9 CV Tailoring.

---

## 📋 LESSONS LEARNED FROM PHASE 9 (CRITICAL)

### Lesson 1: Complete Test Suite = 150-200+ Tests
**Problem:** Initially claimed Gate 4 complete with only 62 tests when target was 150-200 tests.
**Solution:** Create ALL test files before marking complete:
- Unit tests (8 files, 120-150 tests)
- Integration tests (2 files, 20-30 tests)
- Infrastructure tests (2 files, 10-15 tests)
- E2E tests (2 files, 10-15 tests)

### Lesson 2: Test-After-Each-Task Enforcement
**Problem:** Engineers might skip test verification between tasks.
**Solution:** In ENGINEER_PROMPT.md, add explicit "Run tests after EVERY task" instruction with verification commands.

### Lesson 3: Comprehensive Handoff Documentation
**Problem:** Engineers need detailed guidance to avoid asking questions.
**Solution:** Create ENGINEER_PROMPT.md (1,500+ lines) with:
- 10 critical CLAUDE.md rules upfront
- Task-by-task pseudo-code
- 50+ verification commands with expected outputs
- 10 common pitfalls with specific solutions

### Lesson 4: Strict Role Separation
**You (Architect):** Design, document, test suite, handoff
**Engineer (Minimax):** Implementation ONLY

**Never:** Write implementation code as Architect
**Always:** Provide complete specifications so Engineer never asks questions

### Lesson 5: Architectural Decisions Must Be Explicit
Document every decision:
- Synchronous vs Async (Cover Letter = Synchronous, like cv_upload_handler.py)
- LLM Model (Haiku 4.5 for cost optimization)
- Timeout Configuration (300 seconds)
- Storage Strategy (DynamoDB with TTL)
- FVS Integration (VERIFIABLE tier for company/role, FLEXIBLE for content)

---

## 🚪 THE 5 GATES (EXECUTE IN ORDER)

### Gate 1: Design & Architecture Documentation ✅

**File to Create:**
- `docs/architecture/COVER_LETTER_DESIGN.md` (30-40KB)

**Required Sections:**

1. **Cover Letter Generation Algorithm**
   - Input synthesis: VPR + Tailored CV + Gap Responses + Company Research
   - Personalization strategy (specific accomplishments, company culture fit)
   - Anti-AI detection patterns (varied sentence structure, natural transitions, no buzzwords)
   - Word count target: 250-400 words
   - Tone calibration: Professional vs enthusiastic vs technical

2. **LLM Integration Strategy**
   - Model: Claude Haiku 4.5 (TaskMode.TEMPLATE)
   - Cost analysis: Input (~12,000 tokens) + Output (~600 tokens) = $0.004-0.006 per letter
   - Fallback: Retry with Sonnet 4.5 if quality score < 0.70
   - Prompt engineering: System prompt + user prompt with VPR context

3. **FVS Integration**
   - **IMMUTABLE (CRITICAL):** None (cover letters are creative content)
   - **VERIFIABLE (WARNING):** Company name, job title (must match job description)
   - **FLEXIBLE (ALLOWED):** All narrative content, accomplishment descriptions, tone

4. **Data Flow Diagram**
   ```
   User Request (cv_id + job_id + preferences)
     ↓
   Retrieve Master CV, Tailored CV, VPR, Gap Responses
     ↓
   Extract Job Requirements + Company Research
     ↓
   Build LLM Prompt (system + user + context)
     ↓
   Generate Cover Letter (Claude Haiku 4.5)
     ↓
   Validate Against FVS (company name, role title)
     ↓
   Calculate Quality Score (personalization + relevance + tone)
     ↓
   Store Artifact in DynamoDB (90-day TTL)
     ↓
   Return TailoredCoverLetterResponse + Download URL
   ```

5. **Quality Scoring Algorithm**
   ```python
   quality_score = (
       0.40 × personalization_score +    # Specific accomplishments cited
       0.35 × relevance_score +          # Job requirements addressed
       0.25 × tone_appropriateness       # Matches company culture
   )
   ```
   - Thresholds: 0.80+ (excellent), 0.70-0.79 (good), 0.60-0.69 (acceptable), <0.60 (retry with Sonnet)

6. **Error Handling Strategy**
   - LLM timeout (300s) → CV_LETTER_GENERATION_TIMEOUT
   - CV not found → CV_NOT_FOUND
   - Job not found → JOB_NOT_FOUND
   - FVS violation (company/role mismatch) → FVS_HALLUCINATION_DETECTED
   - Rate limit exceeded → RATE_LIMIT_EXCEEDED

7. **Performance Considerations**
   - Expected latency: 8-15 seconds (Haiku)
   - Timeout: 300 seconds (5 minutes)
   - Retry strategy: 3 attempts with exponential backoff
   - Caching: None (cover letters are unique per job + CV combination)

8. **Observability**
   - AWS Powertools: @logger, @tracer, @metrics decorators
   - CloudWatch metrics: generation_duration_ms, quality_score, llm_token_count
   - X-Ray tracing: LLM latency, DAL latency, FVS validation time

**Architectural Decisions:**
- ✅ Synchronous Lambda (like cv_upload_handler.py, NOT async SQS pattern)
- ✅ Claude Haiku 4.5 (cost: $0.004-0.006 per letter)
- ✅ 300-second timeout via asyncio.wait_for()
- ✅ DynamoDB artifact storage with 90-day TTL
- ✅ FVS VERIFIABLE tier for company/role, FLEXIBLE for content
- ✅ Quality scoring: 40% personalization + 35% relevance + 25% tone

---

### Gate 2: API Specification ✅

**File to Create:**
- `docs/specs/cover-letter/COVER_LETTER_SPEC.md` (40-50KB)

**Required Sections:**

1. **REST API Endpoint**
   ```
   POST /api/cover-letter
   ```

2. **Request Model (Pydantic)**
   ```python
   class GenerateCoverLetterRequest(BaseModel):
       cv_id: str = Field(..., min_length=1, max_length=255)
       job_id: str = Field(..., min_length=1, max_length=255)
       company_name: str = Field(..., min_length=1, max_length=255)
       job_title: str = Field(..., min_length=1, max_length=255)
       preferences: Optional[CoverLetterPreferences] = None

   class CoverLetterPreferences(BaseModel):
       tone: Literal["professional", "enthusiastic", "technical"] = "professional"
       word_count_target: int = Field(default=300, ge=200, le=500)
       emphasis_areas: Optional[List[str]] = None  # e.g., ["leadership", "python", "aws"]
       include_salary_expectations: bool = False
   ```

3. **Response Model (Pydantic)**
   ```python
   class TailoredCoverLetterResponse(BaseModel):
       success: bool
       cover_letter: Optional[TailoredCoverLetter]
       fvs_validation: Optional[FVSValidationResult]
       quality_score: float = Field(..., ge=0.0, le=1.0)
       code: str  # Result code
       processing_time_ms: int
       cost_estimate: float
       download_url: Optional[str]

   class TailoredCoverLetter(BaseModel):
       cover_letter_id: str
       cv_id: str
       job_id: str
       user_id: str
       company_name: str
       job_title: str
       content: str  # The cover letter text
       word_count: int
       personalization_score: float
       relevance_score: float
       tone_score: float
       generated_at: datetime
   ```

4. **Result Codes**
   - `COVER_LETTER_GENERATED_SUCCESS` (200 OK)
   - `FVS_HALLUCINATION_DETECTED` (400 Bad Request)
   - `CV_LETTER_GENERATION_TIMEOUT` (504 Gateway Timeout)
   - `CV_NOT_FOUND` (404 Not Found)
   - `JOB_NOT_FOUND` (404 Not Found)
   - `VPR_NOT_FOUND` (400 Bad Request - cannot generate without VPR)
   - `RATE_LIMIT_EXCEEDED` (429 Too Many Requests)
   - `INVALID_REQUEST` (400 Bad Request)

5. **HTTP Status Code Mappings**
   | Result Code | HTTP Status | Response Body |
   |-------------|-------------|---------------|
   | COVER_LETTER_GENERATED_SUCCESS | 200 OK | Full TailoredCoverLetterResponse |
   | FVS_HALLUCINATION_DETECTED | 400 Bad Request | Error + FVS violations |
   | CV_LETTER_GENERATION_TIMEOUT | 504 Gateway Timeout | Error message |
   | CV_NOT_FOUND | 404 Not Found | Error message |
   | JOB_NOT_FOUND | 404 Not Found | Error message |
   | VPR_NOT_FOUND | 400 Bad Request | Error + suggestion |
   | RATE_LIMIT_EXCEEDED | 429 Too Many Requests | Error + retry_after |
   | INVALID_REQUEST | 400 Bad Request | Validation errors |

6. **Authentication**
   - Cognito JWT token required
   - Extract user_id from JWT claims
   - Verify user owns cv_id and job_id

7. **Rate Limiting**
   - Free tier: 5 requests per minute per user
   - Premium tier: 15 requests per minute per user
   - Enterprise tier: 50 requests per minute per user

8. **Security**
   - Input validation: company_name (1-255 chars), job_title (1-255 chars)
   - XSS prevention: Sanitize all text inputs
   - CORS: Restrict to CareerVP frontend domains

9. **OpenAPI 3.0 Schema**
   - Include full schema for /api/cover-letter endpoint
   - Include all request/response models
   - Include all error responses with examples

---

### Gate 3: Task Documentation ✅

**Files to Create:**
- `docs/tasks/10-cover-letter/README.md` (6-8KB)
- `docs/tasks/10-cover-letter/task-01-validation.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-02-infrastructure.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-03-cover-letter-logic.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-04-cover-letter-prompt.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-05-fvs-integration.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-06-cover-letter-handler.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-07-dal-extensions.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-08-models.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-09-integration-tests.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-10-e2e-verification.md` (800-1200 lines)
- `docs/tasks/10-cover-letter/task-11-deployment.md` (800-1200 lines)

**Total:** 13 task documentation files (README + 11 tasks + ARCHITECT_PROMPT.md)

**Task Breakdown Structure (README.md):**

| Task | Description | Complexity | Duration | Test File(s) |
|------|-------------|------------|----------|--------------|
| **01** | Validation Utilities | Low | 1 hour | test_validation.py (15-20 tests) |
| **02** | Infrastructure (CDK) | Medium | 2 hours | test_cover_letter_stack.py (10-15 tests) |
| **03** | Cover Letter Logic | High | 3 hours | test_cover_letter_logic.py (25-30 tests) |
| **04** | Cover Letter Prompt | Medium | 2 hours | test_cover_letter_prompt.py (15-20 tests) |
| **05** | FVS Integration | Medium | 2 hours | test_fvs_integration.py (20-25 tests) |
| **06** | Cover Letter Handler | Medium | 2 hours | test_cover_letter_handler_unit.py (15-20 tests) |
| **07** | DAL Extensions | Low | 1 hour | test_cover_letter_dal_unit.py (10-15 tests) |
| **08** | Pydantic Models | Low | 1 hour | test_cover_letter_models.py (20-25 tests) |
| **09** | Integration Tests | Medium | 2 hours | test_cover_letter_handler_integration.py (25-30 tests) |
| **10** | E2E Verification | Medium | 2 hours | test_cover_letter_flow.py (10-15 tests) |
| **11** | Deployment | Low | 1 hour | N/A (manual verification) |

**Total Estimated Duration:** 19 hours

**Dependency Graph:**
```
Task 01 (Validation) [BLOCKING]
    ↓
Task 08 (Models) [BLOCKING]
    ↓
    ├─→ Task 04 (Prompt)
    ├─→ Task 02 (Infrastructure)
    └─→ Task 07 (DAL - Optional)
         ↓
         ├─→ Task 03 (Logic) [BLOCKING]
         └─→ Task 05 (FVS Integration)
              ↓
              Task 06 (Handler) [BLOCKING]
                   ↓
                   Task 09 (Integration Tests)
                        ↓
                        Task 10 (E2E Tests)
                             ↓
                             Task 11 (Deployment)
```

**Each Task File Must Include:**
1. **Purpose**: What this task achieves
2. **Dependencies**: Which tasks must complete first
3. **Implementation Steps**: 10-20 steps with pseudo-code
4. **Verification Commands**: ruff format, ruff check, mypy --strict, pytest
5. **Expected Test Results**: "19 tests passed" or "27 tests passed"
6. **Completion Criteria**: Checklist of requirements

**Example Task Structure (task-03-cover-letter-logic.md):**

```markdown
# Task 03: Cover Letter Generation Logic

## Purpose
Implement core cover letter generation logic with quality scoring.

## Dependencies
- Task 01 (Validation) COMPLETE
- Task 08 (Models) COMPLETE
- Task 04 (Prompt) COMPLETE

## Files to Create
- `src/backend/careervp/logic/cover_letter_generator.py`

## Implementation Steps

### Step 1: Import Dependencies
```python
from typing import Optional
from careervp.models.result import Result, ResultCode
from careervp.models.cover_letter_models import (
    GenerateCoverLetterRequest,
    TailoredCoverLetter,
)
from careervp.logic.prompts.cover_letter_prompt import (
    build_system_prompt,
    build_user_prompt,
)
from careervp.llm.llm_client import LLMClient, TaskMode
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()
```

### Step 2: Define generate_cover_letter Function
```python
@tracer.capture_method
async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    llm_client: LLMClient,
    dal: DynamoDalHandler,
    timeout: int = 300,
) -> Result[TailoredCoverLetter]:
    """Generate personalized cover letter using LLM.

    Args:
        request: Cover letter generation request
        llm_client: LLM client for generation
        dal: DAL handler for data retrieval
        timeout: Max seconds for LLM call

    Returns:
        Result with TailoredCoverLetter or error
    """
    try:
        # Retrieve master CV
        cv_result = await dal.get_cv_by_id(request.cv_id, request.user_id)
        if not cv_result.success:
            return Result.failure(
                error="CV not found",
                code=ResultCode.CV_NOT_FOUND
            )

        # Retrieve VPR (required for personalization)
        vpr_result = await dal.get_vpr_artifact(request.cv_id, request.job_id)
        if not vpr_result.success:
            return Result.failure(
                error="VPR not found - generate VPR first",
                code=ResultCode.VPR_NOT_FOUND
            )

        # Build prompts
        system_prompt = build_system_prompt(request.preferences)
        user_prompt = build_user_prompt(
            cv=cv_result.data,
            vpr=vpr_result.data,
            job_title=request.job_title,
            company_name=request.company_name,
        )

        # Generate cover letter with timeout
        llm_response = await asyncio.wait_for(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task_mode=TaskMode.TEMPLATE,
                model="claude-haiku-4-5",
            ),
            timeout=timeout,
        )

        # Calculate quality score
        quality_score = calculate_quality_score(llm_response)

        # Return result
        return Result.success(
            data=TailoredCoverLetter(...),
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
        )

    except asyncio.TimeoutError:
        return Result.failure(
            error=f"LLM request timed out after {timeout}s",
            code=ResultCode.CV_LETTER_GENERATION_TIMEOUT,
        )
```

[Continue with Steps 3-10...]

## Verification Commands
```bash
cd src/backend

# Format
uv run ruff format careervp/logic/cover_letter_generator.py

# Lint
uv run ruff check --fix careervp/logic/cover_letter_generator.py

# Type check
uv run mypy careervp/logic/cover_letter_generator.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_cover_letter_logic.py -v

# Expected: 27 tests passed
```

## Completion Criteria
- [ ] generate_cover_letter function implemented
- [ ] calculate_quality_score function implemented
- [ ] All error cases handled (timeout, not found, etc.)
- [ ] Tests pass (27/27)
- [ ] ruff format passes
- [ ] mypy --strict passes
```

---

### Gate 4: Test Suite (RED Phase) ✅

**CRITICAL:** Create ALL test files BEFORE marking Gate 4 complete.

**Test Directory Structure:**
```
tests/cover-letter/
├── __init__.py
├── conftest.py (20+ fixtures)
├── unit/
│   ├── __init__.py
│   ├── test_validation.py (19 tests)
│   ├── test_cover_letter_logic.py (27 tests)
│   ├── test_cover_letter_prompt.py (16 tests)
│   ├── test_fvs_integration.py (24 tests)
│   ├── test_cover_letter_handler_unit.py (19 tests)
│   ├── test_cover_letter_dal_unit.py (14 tests)
│   └── test_cover_letter_models.py (27 tests)
├── integration/
│   ├── __init__.py
│   └── test_cover_letter_handler_integration.py (22 tests)
├── infrastructure/
│   ├── __init__.py
│   └── test_cover_letter_stack.py (28 tests)
└── e2e/
    ├── __init__.py
    └── test_cover_letter_flow.py (20 tests)
```

**Total Test Count Target:** 216 tests (matches Phase 9)

**Test Categories:**
- **Unit tests:** 146 tests across 8 files
- **Integration tests:** 22 tests
- **Infrastructure tests:** 28 tests
- **E2E tests:** 20 tests

**conftest.py Fixtures (Minimum 20):**
```python
@pytest.fixture
def sample_master_cv() -> UserCV:
    """Complete UserCV with experience, skills, education."""
    ...

@pytest.fixture
def sample_vpr() -> VPRResponse:
    """Sample VPR with accomplishments and recommendations."""
    ...

@pytest.fixture
def sample_gap_responses() -> List[GapResponse]:
    """Sample gap analysis responses."""
    ...

@pytest.fixture
def sample_job_description() -> str:
    """500-word job posting text."""
    ...

@pytest.fixture
def sample_cover_letter_request(
    sample_master_cv: UserCV,
    sample_vpr: VPRResponse,
) -> GenerateCoverLetterRequest:
    """Valid cover letter generation request."""
    ...

@pytest.fixture
def sample_cover_letter_preferences() -> CoverLetterPreferences:
    """Cover letter preferences with tone/length."""
    ...

@pytest.fixture
def mock_llm_client() -> Mock:
    """Mock LLMClient with generate() method."""
    ...

@pytest.fixture
def mock_dal_handler() -> Mock:
    """Mock DynamoDalHandler."""
    ...

@pytest.fixture
def sample_generated_cover_letter() -> str:
    """Expected cover letter text from LLM."""
    ...

@pytest.fixture
def sample_quality_scores() -> Dict[str, float]:
    """Quality scoring breakdown."""
    ...

[Add 10 more fixtures...]
```

**test_validation.py (19 tests):**
- validate_company_name: valid, empty, too_long, special_chars
- validate_job_title: valid, empty, too_long
- validate_word_count_target: valid, too_low, too_high
- validate_tone: valid, invalid_enum
- validate_emphasis_areas: valid, empty_list, too_many

**test_cover_letter_logic.py (27 tests):**
- generate_cover_letter: success, cv_not_found, vpr_not_found
- calculate_quality_score: high_quality, medium_quality, low_quality
- extract_vpr_context: valid_vpr, empty_vpr
- build_personalization_context: with_gap_responses, without_gap_responses
- handle_llm_timeout: timeout_error, retry_logic
- quality_score_thresholds: excellent, good, acceptable, needs_retry

**test_cover_letter_prompt.py (16 tests):**
- build_system_prompt: professional_tone, enthusiastic_tone, technical_tone
- build_user_prompt: with_vpr, with_gap_responses, with_company_research
- inject_fvs_rules: verifiable_facts_only
- word_count_guidance: 200_words, 400_words, 500_words

**test_fvs_integration.py (24 tests):**
- create_fvs_baseline: from_job_description
- validate_cover_letter: company_name_match, company_name_mismatch (CRITICAL)
- validate_cover_letter: job_title_match, job_title_mismatch (WARNING)
- fvs_result_handling: no_violations, warning_violations, critical_violations

**test_cover_letter_handler_unit.py (19 tests):**
- handler_success: 200_ok_with_download_url
- handler_invalid_cv_id: 404_not_found
- handler_invalid_job_id: 404_not_found
- handler_missing_vpr: 400_bad_request
- handler_fvs_violation: 400_bad_request
- handler_llm_timeout: 504_gateway_timeout
- handler_rate_limit: 429_too_many_requests
- handler_auth: missing_token, invalid_token, expired_token

**test_cover_letter_dal_unit.py (14 tests):**
- save_cover_letter_artifact: success
- get_cover_letter_artifact: exists, not_exists
- delete_cover_letter_artifact: success
- ttl_handling: 90_day_expiration
- versioning: increment_version
- gsi_queries: by_user, by_job

**test_cover_letter_models.py (27 tests):**
- GenerateCoverLetterRequest: valid, invalid_cv_id, invalid_job_id
- CoverLetterPreferences: valid_tone, invalid_tone, word_count_bounds
- TailoredCoverLetter: serialization, deserialization
- TailoredCoverLetterResponse: success_response, error_response
- field_validation: company_name_constraints, job_title_constraints

**test_cover_letter_handler_integration.py (22 tests):**
- full_flow: handler_to_logic_to_dal
- fvs_rejection: company_name_mismatch
- llm_retry: first_attempt_timeout_second_success
- artifact_storage: save_and_retrieve
- rate_limit_enforcement: exceed_limit

**test_cover_letter_stack.py (28 tests):**
- lambda_configuration: timeout_300s, memory_2048mb, env_vars
- api_gateway_route: post_cover_letter_endpoint
- dynamodb_table: with_ttl_and_gsi
- iam_permissions: lambda_role, dynamodb_access
- cors_configuration: allowed_origins

**test_cover_letter_flow.py (20 tests):**
- e2e_success: complete_http_flow
- e2e_auth: jwt_validation
- e2e_error_scenarios: cv_not_found, vpr_missing, fvs_violation
- e2e_download_url: presigned_s3_url_generation

**Verification Command:**
```bash
cd src/backend
uv run pytest tests/cover-letter/ -v --tb=short

# Expected: ALL tests FAIL (no implementation exists)
# Example output:
# tests/cover-letter/unit/test_validation.py::test_validate_company_name_valid FAILED
# tests/cover-letter/unit/test_cover_letter_logic.py::test_generate_cover_letter_success FAILED
# ...
# Total: 216 tests FAILED (ModuleNotFoundError: No module named 'careervp.logic.cover_letter_generator')
```

**DO NOT mark Gate 4 complete until:**
- [ ] 15 test files created
- [ ] 216 tests exist
- [ ] conftest.py has 20+ fixtures
- [ ] All tests FAIL when run (RED phase confirmed)

---

### Gate 5: Handoff Documentation ✅

**Files to Create:**

1. **docs/tasks/10-cover-letter/ARCHITECT_SIGN_OFF.md** (350-400 lines)
   - Executive summary
   - Deliverables summary (34 files)
   - Architecture decisions recap
   - Verification checklist
   - Handoff instructions
   - File inventory

2. **docs/tasks/10-cover-letter/ENGINEER_PROMPT.md** (1,500-2,000 lines)

**ENGINEER_PROMPT.md Structure:**

```markdown
# Phase 10: Cover Letter Generation - Engineer Implementation Guide

**Date:** 2026-02-05
**Phase:** 10 - Cover Letter Generation
**Engineer:** Minimax
**Role:** Implementation ONLY (no design changes)

---

## 🚨 CRITICAL: 10 CLAUDE.MD RULES (READ FIRST)

Before writing ANY code, internalize these rules from CLAUDE.md:

1. **Layered Monarchy (Rule 1 & 4):** Handler → Logic → DAL, with DAL abstraction injection
2. **Security (Rule 2):** Validate all inputs via Pydantic models
3. **Synchronous Pattern (Rule 3):** Use synchronous Lambda (like cv_upload_handler.py)
4. **Result Pattern (Rule 5):** All logic functions return Result[T]
5. **AWS Powertools:** @logger, @tracer, @metrics decorators mandatory
6. **Type Hints:** mypy --strict must pass on all files
7. **Test After Each Task:** Run pytest after EVERY task completion
8. **No Architecture Changes:** Follow specs EXACTLY as written
9. **FVS Validation:** Always call validate_cover_letter() before returning
10. **Cost Optimization:** Use Claude Haiku 4.5 for generation

---

## 📖 PRE-IMPLEMENTATION READING (30 MINUTES)

Read these documents IN ORDER before starting Task 01:

1. **Architecture:** `docs/architecture/COVER_LETTER_DESIGN.md` (10 min)
   - Understand cover letter generation algorithm
   - Review quality scoring formula
   - Study FVS integration strategy

2. **API Specification:** `docs/specs/cover-letter/COVER_LETTER_SPEC.md` (10 min)
   - Memorize request/response models
   - Understand all result codes
   - Review HTTP status mappings

3. **Task List:** `docs/tasks/10-cover-letter/README.md` (5 min)
   - Understand task dependencies
   - Review implementation order
   - Note estimated durations

4. **Existing Patterns:** (5 min)
   - `src/backend/careervp/handlers/cv_upload_handler.py` - Handler pattern
   - `src/backend/careervp/logic/vpr_generator.py` - Logic pattern
   - `src/backend/careervp/logic/fvs_validator.py` - FVS validation pattern

**DO NOT PROCEED until you've read all 4 documents.**

---

## 🔴 PHASE 0: RED TEST VERIFICATION (MANDATORY)

Before implementing ANYTHING, verify all tests FAIL:

```bash
cd src/backend
uv run pytest tests/cover-letter/ -v --tb=short

# Expected output:
# tests/cover-letter/unit/test_validation.py FAILED (ModuleNotFoundError)
# tests/cover-letter/unit/test_cover_letter_logic.py FAILED (ModuleNotFoundError)
# ...
# Total: 216 tests FAILED
```

If tests don't fail, STOP and ask Architect why.

---

## 📋 TASK-BY-TASK IMPLEMENTATION

### Task 01: Validation Utilities (1 hour)

**Purpose:** Create validation functions for cover letter inputs.

**File to Create:**
- `src/backend/careervp/handlers/utils/validation.py`

**Implementation Steps:**

[10-20 steps with pseudo-code, exactly like Phase 9]

**Verification:**
```bash
cd src/backend

# Format
uv run ruff format careervp/handlers/utils/validation.py

# Lint
uv run ruff check --fix careervp/handlers/utils/validation.py

# Type check
uv run mypy careervp/handlers/utils/validation.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_validation.py -v

# Expected: 19 tests PASS
```

**STOP:** Do not proceed to Task 02 until 19 tests PASS.

---

### Task 02: Infrastructure (CDK) (2 hours)

[Similar structure to Task 01]

---

[Continue for all 11 tasks...]

---

## ✅ COMPLETION CHECKLIST

Phase 10 is COMPLETE when ALL of these are checked:

- [ ] All 11 tasks implemented
- [ ] All 216 tests PASS
- [ ] Code coverage ≥ 90%
- [ ] ruff format passes (no changes)
- [ ] ruff check passes (no errors)
- [ ] mypy --strict passes (no errors)
- [ ] Infrastructure deployed to dev
- [ ] E2E tests pass against deployed environment
- [ ] Architect verification APPROVED

**DO NOT claim completion until ALL boxes checked.**

---

## ⚠️ 10 COMMON PITFALLS & SOLUTIONS

### Pitfall 1: Skipping Tests Between Tasks
**Problem:** Implementing multiple tasks before running tests.
**Solution:** Run `pytest tests/cover-letter/unit/test_file.py -v` after EVERY task.

### Pitfall 2: Not Reading Architecture Documents
**Problem:** Making assumptions about requirements.
**Solution:** Re-read COVER_LETTER_DESIGN.md and COVER_LETTER_SPEC.md before each task.

### Pitfall 3: FVS Bypass
**Problem:** Returning cover letter without FVS validation.
**Solution:** ALWAYS call validate_cover_letter() in handler before returning.

[Continue for all 10 pitfalls...]

---

## 📚 REFERENCE PATTERNS

### Handler Pattern (cv_upload_handler.py)
```python
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    # Parse request
    # Call logic layer
    # Return response
```

### Logic Pattern (vpr_generator.py)
```python
async def generate_vpr(
    cv: UserCV,
    llm_client: LLMClient,
    dal: DalHandler,
) -> Result[VPRResponse]:
    try:
        # Business logic
        return Result.success(data=..., code=ResultCode.SUCCESS)
    except Exception as e:
        return Result.failure(error=str(e), code=ResultCode.ERROR)
```

[Add 5-10 more code examples]

---

**Final Reminder:** Test after EVERY task. No exceptions.
```

---

## 🔍 VERIFICATION CHECKLIST (BEFORE MARKING COMPLETE)

Before claiming "Phase 10 architecture COMPLETE", verify:

- [ ] **Gate 1:** COVER_LETTER_DESIGN.md created (30-40KB)
- [ ] **Gate 2:** COVER_LETTER_SPEC.md created (40-50KB)
- [ ] **Gate 3:** 13 task documentation files created (README + 11 tasks)
- [ ] **Gate 4:** 15 test files created (conftest + 14 test files)
- [ ] **Gate 4:** 216 tests exist (run `find tests/cover-letter -name "*.py" | xargs grep "^def test_" | wc -l`)
- [ ] **Gate 4:** All tests FAIL when run (RED phase confirmed)
- [ ] **Gate 5:** ARCHITECT_SIGN_OFF.md created (350-400 lines)
- [ ] **Gate 5:** ENGINEER_PROMPT.md created (1,500-2,000 lines)
- [ ] **Total:** 34 files created (~50,000 lines of documentation and tests)

**DO NOT proceed to Engineer implementation until ALL boxes checked.**

---

## 🎯 SUCCESS CRITERIA

Phase 10 architecture is COMPLETE when:

1. ✅ All design documents created (1 file)
2. ✅ All specifications created (1 file)
3. ✅ All task documentation created (13 files)
4. ✅ Complete test suite created (15 files, 216 tests)
5. ✅ All tests FAIL (RED phase confirmed)
6. ✅ Handoff documentation created (2 files)
7. ✅ Follows Layered Monarchy pattern
8. ✅ Follows Result[T] pattern
9. ✅ Follows existing patterns (cv_upload_handler.py, fvs_validator.py)
10. ✅ Security requirements documented
11. ✅ Observability requirements documented
12. ✅ FVS integration requirements documented

**Total Files:** 34 files delivered
**Total Lines:** ~50,000 lines of documentation and tests

---

## 🚀 EXECUTION INSTRUCTIONS

As the Architect, execute this prompt by:

1. **Read Phase 9 deliverables** (for pattern reference):
   - docs/architecture/CV_TAILORING_DESIGN.md
   - docs/specs/cv-tailoring/CV_TAILORING_SPEC.md
   - docs/tasks/09-cv-tailoring/ENGINEER_PROMPT.md

2. **Execute Gate 1:** Create COVER_LETTER_DESIGN.md
   - Use writer agent for documentation
   - Reference CV_TAILORING_DESIGN.md for structure
   - Adapt for cover letter generation specifics

3. **Execute Gate 2:** Create COVER_LETTER_SPEC.md
   - Use writer agent for documentation
   - Define all Pydantic models
   - Define all result codes and HTTP mappings

4. **Execute Gate 3:** Create 13 task documentation files
   - Use writer agent for each task file
   - Each task: 800-1200 lines with pseudo-code
   - Follow task-XX-*.md pattern from Phase 9

5. **Execute Gate 4:** Create complete test suite (216 tests)
   - Start with conftest.py (20+ fixtures)
   - Create ALL 14 test files (unit + integration + infrastructure + e2e)
   - Verify test count: `find tests/cover-letter -name "*.py" | xargs grep "^def test_" | wc -l`
   - Run tests to confirm ALL FAIL (RED phase)

6. **Execute Gate 5:** Create handoff documentation
   - ARCHITECT_SIGN_OFF.md: Executive summary + verification
   - ENGINEER_PROMPT.md: 1,500-2,000 lines implementation guide

7. **Final Verification:**
   - Count files: 34 total
   - Count tests: 216 total
   - Verify all tests FAIL
   - Mark Phase 10 architecture COMPLETE

---

## 📝 ARCHITECTURAL PATTERN SUMMARY

**Core Patterns to Follow:**

| Pattern | Description | Example |
|---------|-------------|---------|
| **Layered Monarchy** | Handler → Logic → DAL | cv_upload_handler.py → vpr_generator.py → dynamo_dal_handler.py |
| **Result[T]** | Typed result objects | `Result.success(data=..., code=...)` |
| **FVS Validation** | Three-tier fact checking | IMMUTABLE (none), VERIFIABLE (company/role), FLEXIBLE (content) |
| **AWS Powertools** | Observability decorators | @logger, @tracer, @metrics |
| **Pydantic Models** | Request/response validation | GenerateCoverLetterRequest, TailoredCoverLetterResponse |
| **Claude Haiku 4.5** | Cost-optimized LLM | TaskMode.TEMPLATE, $0.004-0.006 per letter |
| **Synchronous Lambda** | Direct request/response | Like cv_upload_handler.py, NOT async SQS |
| **DynamoDB Artifacts** | 90-day TTL storage | PK=user_id, SK=ARTIFACT#COVER_LETTER#... |

---

## 🔗 REFERENCE FILES

**Existing Patterns (Study These):**
- `src/backend/careervp/handlers/cv_upload_handler.py` - Handler pattern
- `src/backend/careervp/logic/vpr_generator.py` - Logic pattern
- `src/backend/careervp/logic/fvs_validator.py` - FVS validation pattern
- `src/backend/careervp/dal/dynamo_dal_handler.py` - DAL pattern
- `tests/cv-tailoring/conftest.py` - Fixture patterns

**Phase 9 Reference (Template for Phase 10):**
- `docs/architecture/CV_TAILORING_DESIGN.md` - Architecture template
- `docs/specs/cv-tailoring/CV_TAILORING_SPEC.md` - API spec template
- `docs/tasks/09-cv-tailoring/README.md` - Task breakdown template
- `docs/tasks/09-cv-tailoring/ENGINEER_PROMPT.md` - Engineer guide template
- `tests/cv-tailoring/unit/test_tailoring_logic.py` - Unit test template

---

## 🎓 LESSONS LEARNED CHECKLIST

Apply these lessons from Phase 9:

- [x] **Complete Test Suite:** Create ALL 216 tests before marking Gate 4 complete
- [x] **Test-After-Each-Task:** Enforce in ENGINEER_PROMPT.md
- [x] **Comprehensive Handoff:** ENGINEER_PROMPT.md must be 1,500+ lines
- [x] **Strict Role Separation:** Architect documents, Engineer implements
- [x] **Explicit Decisions:** Document all architectural decisions with rationale
- [x] **Quality Thresholds:** Define scoring algorithm and thresholds upfront
- [x] **Error Handling:** Map ALL error cases to result codes and HTTP statuses
- [x] **Cost Optimization:** Calculate cost per operation, optimize with Haiku
- [x] **FVS Integration:** Define three-tier validation for domain entities
- [x] **Observability:** Mandate AWS Powertools decorators everywhere

---

**END OF ARCHITECT PROMPT**

---

## 🎯 FINAL INSTRUCTIONS

Execute this prompt as the **Lead Architect** for Phase 10: Cover Letter Generation.

Your deliverables:
1. Complete architecture documentation (34 files)
2. Complete test suite (216 tests, RED phase)
3. Comprehensive handoff documentation (ENGINEER_PROMPT.md 1,500+ lines)

Your responsibility ENDS when Engineer (Minimax) has everything needed to implement without asking questions.

**Status after completion:** Phase 10 architecture 100% COMPLETE, ready for Engineer implementation.
