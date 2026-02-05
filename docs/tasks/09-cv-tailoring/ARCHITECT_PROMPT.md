# Phase 9: CV Tailoring - Architect Prompt

**Date:** 2026-02-04
**Phase:** 9 - CV Tailoring
**Your Role:** Lead Architect (Design, Specification, Testing ONLY - NO Implementation)
**Model for Success:** Phase 11 Gap Analysis (100% architectural completion)

---

## 🎯 MISSION STATEMENT

Design and architect the **CV Tailoring** feature using **strict Test-Driven Development (TDD)** methodology. You will create comprehensive architecture documentation, detailed specifications, granular task breakdowns, and a complete test suite (RED phase) for the Engineer to implement.

**CRITICAL:** You are the **Architect ONLY**. You do NOT write implementation code. Your deliverables are documentation and tests.

---

## 🚫 ROLE BOUNDARIES (CRITICAL)

### ✅ YOU MUST DO (Architect Responsibilities):
- [ ] Research existing patterns (VPR, Gap Analysis)
- [ ] Design architecture and data flow
- [ ] Write specifications with API contracts
- [ ] Create granular task documentation
- [ ] Write complete test suite (unit, integration, infrastructure, e2e)
- [ ] Verify all tests FAIL initially (RED phase)
- [ ] Create handoff documentation (ARCHITECT_SIGN_OFF.md, ENGINEER_PROMPT.md)
- [ ] Document architectural decisions

### ❌ YOU MUST NOT DO (Engineer Responsibilities):
- [ ] ~~Write implementation code~~ (handlers, logic, models)
- [ ] ~~Fix failing tests with implementation~~
- [ ] ~~Deploy infrastructure~~
- [ ] ~~Run GREEN tests~~
- [ ] ~~Perform integration testing~~

**If you find yourself writing `def`, `class`, `async def`, or implementation logic → STOP. You are violating role boundaries.**

---

## 📋 PHASE 9 OVERVIEW: CV TAILORING

### Feature Description

CV Tailoring generates a customized resume tailored to a specific job description. The feature:

1. **Accepts Input:**
   - User's master CV (structured CV model)
   - Target job description (text)
   - Tailoring preferences (optional: tone, emphasis, length)

2. **Performs Analysis:**
   - Identifies relevant skills and experiences from master CV
   - Matches CV content to job requirements
   - Prioritizes most relevant information
   - Applies FVS (Fact Verification System) validation

3. **Generates Output:**
   - Tailored CV optimized for the specific job
   - Explanation of changes made
   - Relevance scores for included content
   - FVS validation results

### Key Architectural Decisions (To Be Determined)

You will need to decide:

- **Synchronous vs Async:** Follow Phase 11 pattern (synchronous Lambda) or use Phase 10 pattern (async SQS)?
- **LLM Model:** Claude Haiku 4.5 (cost-optimized) or Claude Sonnet 4.5 (quality-optimized)?
- **Timeout:** 300 seconds (for Haiku) or 600 seconds (for Sonnet)?
- **Scoring Algorithm:** How to calculate relevance scores for CV sections?
- **FVS Integration:** How to validate tailored CV content against original facts?
- **Storage Strategy:** Store tailored CVs as artifacts in DynamoDB? TTL?

**Reference Phase 11 for decision-making patterns.**

---

## 🚦 TDD WORKFLOW GATES (MANDATORY SEQUENCE)

### Gate 1: Architecture & Design
**Deliverables:**
1. **`docs/architecture/CV_TAILORING_DESIGN.md`**
   - CV tailoring algorithm and matching logic
   - Relevance scoring system
   - Content prioritization strategy
   - FVS integration approach
   - Data flow diagram (User Input → Analysis → Tailored CV)
   - LLM prompt strategy

2. **`docs/architecture/FVS_INTEGRATION.md`** (if needed)
   - How FVS validates tailored content
   - Fact extraction from master CV
   - Validation rules and error handling

**Verification:** Files exist and contain comprehensive design decisions.

---

### Gate 2: Specification
**Deliverables:**
1. **`docs/specs/cv-tailoring/CV_TAILORING_SPEC.md`**
   - API endpoint: `POST /api/cv-tailoring`
   - Request model: `TailorCVRequest` (Pydantic)
     ```python
     class TailorCVRequest(BaseModel):
         cv_id: str
         job_description: str
         preferences: Optional[TailoringPreferences]
     ```
   - Response model: `TailorCVResponse` (Pydantic)
     ```python
     class TailorCVResponse(BaseModel):
         tailored_cv: CV
         changes_made: list[str]
         relevance_scores: dict[str, float]
         fvs_validation: FVSValidationResult
     ```
   - Result codes:
     - `CV_TAILORED_SUCCESS`
     - `CV_TAILORING_FAILED`
     - `FVS_VALIDATION_FAILED`
   - Error handling strategy
   - Authentication and authorization
   - Rate limiting
   - OpenAPI schema

**Verification:** Specification is complete and unambiguous. Engineer can implement without questions.

---

### Gate 3: Task Breakdown
**Deliverables:**
1. **`docs/tasks/09-cv-tailoring/README.md`**
   - Overview of all tasks
   - Dependency graph
   - Estimated complexity per task

2. **Task Files (Create 9-12 atomic task files):**
   - `task-01-validation.md` - Input validation utilities
   - `task-02-infrastructure.md` - CDK infrastructure (Lambda, API Gateway)
   - `task-03-tailoring-logic.md` - Core CV tailoring algorithm
   - `task-04-tailoring-prompt.md` - LLM prompt engineering
   - `task-05-fvs-integration.md` - FVS validation integration
   - `task-06-tailoring-handler.md` - Lambda handler implementation
   - `task-07-dal-extensions.md` - DynamoDB artifact storage (OPTIONAL)
   - `task-08-models.md` - Pydantic models for requests/responses
   - `task-09-integration-tests.md` - Integration test verification
   - `task-10-e2e-verification.md` - End-to-end testing
   - `task-11-deployment.md` - Deployment and monitoring

**Each task file must include:**
- Purpose and scope
- Implementation steps (pseudo-code, NOT real code)
- Verification commands (pytest, ruff, mypy)
- Expected test results
- Files to create/modify
- Dependencies on other tasks

**Verification:** All tasks are atomic (completable in 1-2 hours), have clear success criteria, and map to test files.

---

### Gate 4: Test Suite (RED Phase)
**Deliverables:**

Create complete test directory structure:

```
tests/cv-tailoring/
├── __init__.py
├── conftest.py                              # Pytest fixtures (20+ fixtures)
├── unit/
│   ├── __init__.py
│   ├── test_validation.py                   # Task 01 (15-20 tests)
│   ├── test_tailoring_logic.py              # Task 03 (25-30 tests)
│   ├── test_tailoring_prompt.py             # Task 04 (15-20 tests)
│   ├── test_fvs_integration.py              # Task 05 (20-25 tests)
│   ├── test_tailoring_handler_unit.py       # Task 06 (15-20 tests)
│   ├── test_tailoring_dal_unit.py           # Task 07 (10-15 tests, OPTIONAL)
│   └── test_tailoring_models.py             # Task 08 (20-25 tests)
├── integration/
│   ├── __init__.py
│   └── test_tailoring_handler_integration.py # Task 09 (25-30 tests)
├── infrastructure/
│   ├── __init__.py
│   └── test_cv_tailoring_stack.py           # Task 02 (10-15 tests)
└── e2e/
    ├── __init__.py
    └── test_cv_tailoring_flow.py            # Task 10 (10-15 tests)
```

**Test Requirements:**
- **Total tests:** 150-200 tests
- **Coverage target:** 90%+ for new code
- **All tests MUST fail initially** (no implementation exists)
- Use pytest fixtures from `conftest.py`
- Mock LLMClient for predictable outputs
- Mock DynamoDB via moto or direct mocking
- Mock FVS calls with sample validation results

**Test-to-Task Mapping:**
| Task | Test File | Expected Test Count |
|------|-----------|---------------------|
| 01 | test_validation.py | 15-20 tests |
| 02 | test_cv_tailoring_stack.py | 10-15 tests |
| 03 | test_tailoring_logic.py | 25-30 tests |
| 04 | test_tailoring_prompt.py | 15-20 tests |
| 05 | test_fvs_integration.py | 20-25 tests |
| 06 | test_tailoring_handler_unit.py | 15-20 tests |
| 07 | test_tailoring_dal_unit.py | 10-15 tests (OPTIONAL) |
| 08 | test_tailoring_models.py | 20-25 tests |
| 09 | test_tailoring_handler_integration.py | 25-30 tests |
| 10 | test_cv_tailoring_flow.py | 10-15 tests |

**Verification Commands:**
```bash
# RED Phase Verification (all tests MUST fail)
cd src/backend
uv run pytest tests/cv-tailoring/ -v --tb=short
# Expected: 150-200 tests FAIL with "ModuleNotFoundError" or "No implementation"
```

---

### Gate 5: Handoff Documentation
**Deliverables:**

1. **`docs/tasks/09-cv-tailoring/ARCHITECT_SIGN_OFF.md`**
   - Executive summary
   - Deliverables checklist (all files created)
   - Architecture decisions documented
   - Verification checklist
   - Handoff instructions for Engineer

2. **`docs/tasks/09-cv-tailoring/ENGINEER_PROMPT.md`**
   - Mission statement with all CLAUDE.md rules
   - Pre-implementation reading checklist
   - Phase 0: RED test verification
   - Task-by-task implementation guide (9-12 tasks)
   - Test-after-each-task enforcement
   - Deployment guide
   - Completion checklist
   - Common pitfalls section
   - Reference files section

**Verification:** Engineer (Minimax) has everything needed to begin implementation without asking questions.

---

## 🏗️ ARCHITECTURAL PATTERNS (MANDATORY)

### 1. Layered Monarchy Pattern
**Rule:** Handler → Logic → DAL (with DAL abstraction injection)

```
┌─────────────────────────────────────┐
│  handlers/cv_tailoring_handler.py   │  ← Lambda entry point
│  - Input validation (Pydantic)      │  ← AWS Powertools decorators
│  - Call logic layer                 │  ← Error handling
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  logic/cv_tailoring.py              │  ← Core business logic
│  - Tailor CV algorithm              │  ← Returns Result[T]
│  - FVS validation                   │  ← No AWS SDK calls
│  - LLM prompt construction          │  ← Uses DalHandler interface
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  dal/dynamo_dal_handler.py          │  ← Data access layer
│  - Store tailored CV artifact       │  ← Implements DalHandler
│  - Retrieve master CV               │  ← DynamoDB operations
└─────────────────────────────────────┘
```

**Handler must:**
- Validate input via Pydantic models
- Use AWS Powertools decorators (`@logger`, `@tracer`, `@metrics`)
- Call logic layer, handle Result[T] response
- Convert Result to API response (200/400/500)

**Logic must:**
- Return `Result[T]` for all functions
- Accept `DalHandler` interface (NOT concrete class)
- Contain NO AWS SDK calls
- Be 100% unit testable with mocks

**DAL must:**
- Implement `DalHandler` interface
- Handle all DynamoDB operations
- Follow PK/SK pattern: `pk=user_id`, `sk=ARTIFACT#CV_TAILORED#{cv_id}#{job_id}#v{version}`

---

### 2. Result[T] Pattern
**Rule:** All logic functions return `Result[T]`

```python
from careervp.models.result import Result, ResultCode

def tailor_cv(
    cv: CV,
    job_description: str,
    dal: DalHandler
) -> Result[TailoredCV]:
    """Tailor CV to job description."""
    # Implementation by Engineer
    pass
```

**Result structure:**
```python
@dataclass
class Result:
    success: bool
    data: Optional[Any]
    error: Optional[str]
    code: ResultCode
```

---

### 3. Security Validation
**Rule:** Enforce limits via `handlers/utils/validation.py`

```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 1_000_000       # 1M characters
MAX_JOB_DESCRIPTION_LENGTH = 50_000  # 50K characters

def validate_file_size(content: bytes) -> None:
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(f"File exceeds {MAX_FILE_SIZE} bytes")

def validate_text_length(text: str) -> None:
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text exceeds {MAX_TEXT_LENGTH} characters")
```

---

### 4. FVS Integration Pattern
**Rule:** Validate all tailored content against original CV facts

```python
def validate_tailored_cv(
    original_cv: CV,
    tailored_cv: CV,
    fvs_client: FVSClient
) -> Result[FVSValidationResult]:
    """Validate tailored CV against FVS."""
    # Extract facts from original CV
    # Validate each statement in tailored CV
    # Return validation result with confidence scores
    pass
```

---

### 5. LLM Integration Pattern
**Rule:** Use Claude Haiku 4.5 or Sonnet 4.5 with timeout

**Decision Points:**
- **Haiku:** Fast (5-10s), cheap, good for straightforward tailoring
- **Sonnet:** Slower (15-30s), expensive, better for complex reasoning

```python
import asyncio
from careervp.services.llm_client import LLMClient

async def tailor_cv_with_llm(
    cv: CV,
    job_description: str,
    llm_client: LLMClient
) -> str:
    """Call LLM to tailor CV."""
    try:
        response = await asyncio.wait_for(
            llm_client.generate(...),
            timeout=300.0  # 5 minutes for Haiku
        )
        return response
    except asyncio.TimeoutError:
        raise TimeoutError("LLM call timed out")
```

---

### 6. Observability Pattern
**Rule:** Use AWS Powertools for logging, tracing, and metrics

```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="cv-tailoring")
tracer = Tracer(service="cv-tailoring")
metrics = Metrics(namespace="CareerVP", service="cv-tailoring")

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """POST /api/cv-tailoring endpoint."""
    # Implementation by Engineer
    pass
```

---

## 🧪 TEST-AFTER-EACH-TASK ENFORCEMENT

**CRITICAL RULE:** After completing EACH task implementation, the Engineer MUST:

1. **Format code:**
   ```bash
   uv run ruff format careervp/path/to/file.py
   ```

2. **Lint code:**
   ```bash
   uv run ruff check --fix careervp/path/to/file.py
   ```

3. **Type-check code:**
   ```bash
   uv run mypy careervp/path/to/file.py --strict
   ```

4. **Run tests for THIS task:**
   ```bash
   uv run pytest tests/cv-tailoring/unit/test_file.py -v
   # Expected: All tests for this task PASS
   ```

5. **Mark task as COMPLETE** only when all tests pass.

**Example (Task 03: Tailoring Logic):**
```bash
# Step 1: Format
uv run ruff format careervp/logic/cv_tailoring.py

# Step 2: Lint
uv run ruff check --fix careervp/logic/cv_tailoring.py

# Step 3: Type-check
uv run mypy careervp/logic/cv_tailoring.py --strict

# Step 4: Run tests
uv run pytest tests/cv-tailoring/unit/test_tailoring_logic.py -v
# Expected: 25-30 tests PASS

# Step 5: Mark complete
✅ Task 03 Complete
```

---

## ✅ VERIFICATION COMMANDS

### Phase 0: RED Test Verification (Before Implementation)
```bash
cd src/backend
uv run pytest tests/cv-tailoring/ -v --tb=short
# Expected: 150-200 tests FAIL
```

### Phase 1: Unit Test Verification (After Implementation)
```bash
cd src/backend
uv run pytest tests/cv-tailoring/unit/ -v --cov=careervp --cov-report=term-missing
# Expected: All unit tests PASS, coverage ≥90%
```

### Phase 2: Integration Test Verification
```bash
cd src/backend
uv run pytest tests/cv-tailoring/integration/ -v
# Expected: All integration tests PASS
```

### Phase 3: Infrastructure Test Verification
```bash
cd infra
npx cdk synth
uv run pytest tests/infrastructure/test_cv_tailoring_stack.py -v
# Expected: All infrastructure assertions PASS
```

### Phase 4: E2E Test Verification
```bash
cd src/backend
uv run pytest tests/cv-tailoring/e2e/ -v
# Expected: All E2E tests PASS
```

### Phase 5: Coverage Check
```bash
cd src/backend
uv run pytest tests/cv-tailoring/ -v --cov=careervp --cov-report=html
# Expected: Coverage ≥90%
# Open htmlcov/index.html to view detailed report
```

### Phase 6: Code Quality Check
```bash
cd src/backend

# Format
uv run ruff format .

# Lint
uv run ruff check --fix .

# Type check
uv run mypy careervp --strict

# All checks should pass with no errors
```

---

## 📄 HANDOFF DOCUMENTATION REQUIREMENTS

### ARCHITECT_SIGN_OFF.md Must Include:

1. **Executive Summary**
   - Status: ARCHITECTURE COMPLETE
   - Date of sign-off
   - Architect certification

2. **Deliverables Summary**
   - All files created (with byte sizes)
   - Architecture documents
   - Specifications
   - Task documentation
   - Test suite details

3. **Architecture Decisions**
   - Synchronous vs async decision
   - LLM model choice (Haiku vs Sonnet)
   - Timeout configuration
   - FVS integration approach
   - Storage strategy

4. **Verification Checklist**
   - [ ] All design documents created
   - [ ] All specifications created
   - [ ] All task documentation created
   - [ ] Complete test suite created (150-200 tests)
   - [ ] Unit test for each task
   - [ ] Integration test coverage
   - [ ] Infrastructure test coverage
   - [ ] E2E test coverage
   - [ ] Follows Layered Monarchy pattern
   - [ ] Follows Result[T] pattern
   - [ ] Security requirements documented
   - [ ] Observability requirements documented

5. **Handoff Instructions**
   - Start here: Review architecture
   - Run RED tests
   - Begin implementation (task order)
   - Run GREEN tests
   - Deploy and verify

---

### ENGINEER_PROMPT.md Must Include:

1. **Mission Statement**
   - Clear objective for Engineer
   - List of 10 critical rules from CLAUDE.md

2. **Pre-Implementation Reading Checklist**
   - [ ] Read `docs/architecture/CV_TAILORING_DESIGN.md`
   - [ ] Read `docs/specs/cv-tailoring/CV_TAILORING_SPEC.md`
   - [ ] Read `docs/tasks/09-cv-tailoring/README.md`
   - [ ] Scan existing patterns: `handlers/vpr_handler.py`, `logic/vpr_generator.py`

3. **Phase 0: RED Test Verification**
   ```bash
   cd src/backend
   uv run pytest tests/cv-tailoring/ -v --tb=short
   # Expected: All tests FAIL
   ```

4. **Task-by-Task Implementation Guide (9-12 tasks)**
   - Each task section includes:
     - Purpose and scope
     - Implementation steps with pseudo-code
     - Verification commands (ruff, mypy)
     - Test execution commands
     - Expected test count and results
     - Completion criteria

5. **Deployment Guide**
   - Final verification checklist
   - CDK deployment commands
   - Post-deployment verification
   - Test live endpoint with curl

6. **Completion Checklist**
   - [ ] Code Quality: ruff format, ruff check, mypy --strict pass
   - [ ] Testing: 150-200 tests pass, coverage ≥90%
   - [ ] Deployment: Lambda exists, API Gateway route accessible
   - [ ] Documentation: All patterns followed

7. **Common Pitfalls Section**
   - Do NOT skip tests
   - Do NOT modify architecture
   - Do NOT change API contracts
   - Do NOT skip format/lint/type-check
   - Do NOT deploy without verification
   - Do NOT claim completion without evidence
   - Do NOT violate Layered Monarchy pattern

8. **Reference Files Section**
   - Links to all 30+ deliverable files
   - Links to existing patterns (VPR, Gap Analysis)

---

## ⚠️ COMMON PITFALLS (DO NOT MAKE THESE MISTAKES)

### Pitfall 1: Scope Creep (Architect Writing Implementation)
**Symptom:** You find yourself writing `def`, `class`, `async def`, or implementation logic.

**Solution:** STOP immediately. Write pseudo-code or comments instead. Reference existing patterns.

**Example (WRONG):**
```python
# ❌ WRONG: Architect writing implementation
def tailor_cv(cv: CV, job_description: str) -> TailoredCV:
    # Parse job description
    keywords = extract_keywords(job_description)
    # Filter CV sections
    relevant_sections = filter_sections(cv, keywords)
    # Generate tailored CV
    return TailoredCV(sections=relevant_sections)
```

**Example (CORRECT):**
```python
# ✅ CORRECT: Architect providing guidance
def tailor_cv(cv: CV, job_description: str, dal: DalHandler) -> Result[TailoredCV]:
    """
    Tailor CV to job description.

    Implementation steps:
    1. Extract keywords from job_description using LLM
    2. Score each CV section for relevance (0.0-1.0)
    3. Filter sections with score < 0.3
    4. Reorder sections by relevance score (descending)
    5. Apply FVS validation to tailored content
    6. Return Result[TailoredCV] with validation results

    Reference: handlers/vpr_handler.py for similar pattern
    """
    pass  # Implementation by Engineer
```

---

### Pitfall 2: Incomplete Test Coverage
**Symptom:** Some tasks don't have corresponding test files, or tests don't cover edge cases.

**Solution:** Create a test file for EACH task. Use the Test-to-Task Mapping table.

**Checklist:**
- [ ] Every task has a corresponding test file
- [ ] Tests cover happy path, error paths, edge cases
- [ ] Tests use mocks for external dependencies (LLM, DynamoDB, FVS)
- [ ] Tests validate Result[T] structure (success, data, error, code)

---

### Pitfall 3: Ambiguous Specifications
**Symptom:** Specification leaves room for interpretation. Engineer will need to ask questions.

**Solution:** Make specifications unambiguous. Include:
- Exact API endpoint path and HTTP method
- Complete Pydantic models with field types and validation rules
- All possible response codes (success and error)
- Example request/response payloads
- Authentication requirements
- Rate limiting rules

---

### Pitfall 4: Missing Architecture Decisions
**Symptom:** You haven't decided on synchronous vs async, LLM model, timeout, scoring algorithm, etc.

**Solution:** Make ALL architectural decisions upfront. Document them in `CV_TAILORING_DESIGN.md`.

**Decision Checklist:**
- [ ] Synchronous or async implementation?
- [ ] LLM model (Haiku or Sonnet)?
- [ ] Timeout value?
- [ ] Scoring algorithm for relevance?
- [ ] FVS integration approach?
- [ ] Storage strategy (DynamoDB artifact pattern)?
- [ ] TTL for stored artifacts?

---

### Pitfall 5: Forgetting Test-After-Each-Task
**Symptom:** Engineer implements multiple tasks before running tests. Tests fail in bulk.

**Solution:** Enforce test-after-each-task in ENGINEER_PROMPT.md. Each task section must include:
1. Implementation steps
2. Verification commands (ruff, mypy)
3. Test execution command
4. Expected test count and results
5. Completion criteria

---

### Pitfall 6: No Common Pitfalls Section
**Symptom:** Engineer makes preventable mistakes (skipping tests, violating patterns, changing API contracts).

**Solution:** Add a "Common Pitfalls" section to ENGINEER_PROMPT.md with 7-10 specific mistakes to avoid.

---

### Pitfall 7: Missing Reference to Phase 11
**Symptom:** You're reinventing patterns that already exist in Phase 11 Gap Analysis.

**Solution:** Constantly reference Phase 11 as a model. Copy the structure, patterns, and workflow.

**Phase 11 Reference Checklist:**
- [ ] Same directory structure (`docs/architecture/`, `docs/specs/`, `docs/tasks/09-cv-tailoring/`)
- [ ] Same task file structure (`task-01-validation.md`, `task-02-infrastructure.md`, etc.)
- [ ] Same test structure (`tests/cv-tailoring/unit/`, `integration/`, `infrastructure/`, `e2e/`)
- [ ] Same handoff documents (`ARCHITECT_SIGN_OFF.md`, `ENGINEER_PROMPT.md`)
- [ ] Same verification commands
- [ ] Same test-to-task mapping approach

---

## 📚 REFERENCE: PHASE 11 AS A MODEL

### Phase 11 Deliverables (Use as Template)

**Architecture & Design (2 files):**
1. `docs/architecture/GAP_ANALYSIS_DESIGN.md` (16,247 bytes)
2. `docs/architecture/VPR_ASYNC_DESIGN.md` (9,482 bytes) ← For future async phases

**Specification (1 file):**
1. `docs/specs/gap-analysis/GAP_SPEC.md` (20,764 bytes)

**Task Documentation (11 files):**
1. `docs/tasks/11-gap-analysis/README.md` (6,403 bytes)
2. `task-01-async-foundation.md`
3. `task-02-infrastructure.md`
4. `task-03-gap-analysis-logic.md`
5. `task-04-gap-analysis-prompt.md`
6. `task-05-gap-handler.md`
7. `task-06-dal-extensions.md` (OPTIONAL)
8. `task-07-integration-tests.md`
9. `task-08-e2e-verification.md`
10. `task-09-deployment.md`

**Test Suite (15 files, 150+ tests):**
- `tests/gap-analysis/conftest.py` (20+ fixtures)
- Unit tests: 6 files
- Integration tests: 2 files
- Infrastructure tests: 1 file
- E2E tests: 1 file

**Handoff Documentation (2 files):**
1. `docs/tasks/11-gap-analysis/ARCHITECT_SIGN_OFF.md`
2. `docs/tasks/11-gap-analysis/ENGINEER_PROMPT.md`

**Total:** 27 files, ~18,000 lines of documentation and tests

---

### Phase 11 Patterns to Copy

1. **Gap Scoring Algorithm:**
   ```python
   gap_score = (0.7 × impact_score) + (0.3 × probability_score)
   where: HIGH=1.0, MEDIUM=0.6, LOW=0.3
   ```

   **Phase 9 Equivalent:** Design a relevance scoring algorithm
   ```python
   relevance_score = f(skill_match, experience_match, keyword_match)
   ```

2. **LLM Integration:**
   - Model: Claude Haiku 4.5
   - Timeout: 600 seconds via `asyncio.wait_for()`
   - Max output: 5 questions per analysis

   **Phase 9 Equivalent:** Decide on model and timeout for CV tailoring

3. **Security Validation:**
   - 10MB file size limit
   - 1M character text limit
   - Validation via `handlers/utils/validation.py`

   **Phase 9 Equivalent:** Same limits, plus job description length limit (50K characters)

4. **Synchronous Implementation:**
   - Phase 11 uses synchronous Lambda (NOT async SQS)
   - Follows existing VPR pattern

   **Phase 9 Decision:** Should CV tailoring be synchronous or async? (Recommend synchronous for consistency)

5. **DynamoDB Artifact Pattern (OPTIONAL):**
   - PK: `user_id`
   - SK: `ARTIFACT#GAP#{cv_id}#{job_id}#v{version}`
   - 90-day TTL

   **Phase 9 Equivalent:** PK: `user_id`, SK: `ARTIFACT#CV_TAILORED#{cv_id}#{job_id}#v{version}`

---

## 🧩 LESSONS LEARNED FROM PHASE 11

### Lesson 1: Strict Role Separation
**What Happened:** Initial confusion about Architect vs Engineer roles. Architect started writing implementation code.

**What We Learned:** Architect ONLY does design, spec, tests. Engineer ONLY does implementation.

**Application to Phase 9:** Be vigilant about role boundaries. If you write `def`, STOP.

---

### Lesson 2: Test-After-Each-Task is Critical
**What Happened:** Without explicit enforcement, Engineer might implement multiple tasks before testing, leading to bulk failures.

**What We Learned:** Each task in ENGINEER_PROMPT.md must include verification and test commands.

**Application to Phase 9:** Every task section must end with:
```bash
# Step 4: Run tests for THIS task
uv run pytest tests/cv-tailoring/unit/test_file.py -v
# Expected: X tests PASS

✅ Task N Complete
```

---

### Lesson 3: Complete Test Suite Before Implementation
**What Happened:** Phase 11 created 150+ tests before any implementation. All tests failed initially (RED phase).

**What We Learned:** TDD workflow is: Tests (RED) → Implementation (GREEN) → Refactor. Never start with implementation.

**Application to Phase 9:** Create 150-200 tests BEFORE Engineer writes any code. Verify all tests fail.

---

### Lesson 4: Comprehensive Task Documentation
**What Happened:** Task files included pseudo-code, verification commands, and expected outcomes.

**What We Learned:** Detailed task documentation prevents Engineer from asking clarifying questions.

**Application to Phase 9:** Each task file should be so detailed that Engineer can implement without asking questions.

---

### Lesson 5: Handoff Documentation is Essential
**What Happened:** Phase 11 created ARCHITECT_SIGN_OFF.md and ENGINEER_PROMPT.md for clear handoff.

**What We Learned:** Handoff documents ensure Engineer knows exactly what to do and what success looks like.

**Application to Phase 9:** Create the same handoff documents. ARCHITECT_SIGN_OFF.md certifies completion. ENGINEER_PROMPT.md guides implementation.

---

### Lesson 6: Common Pitfalls Section Prevents Mistakes
**What Happened:** ENGINEER_PROMPT.md included a section listing 7 common mistakes to avoid.

**What We Learned:** Proactive error prevention is more efficient than reactive debugging.

**Application to Phase 9:** Include a "Common Pitfalls" section with 7-10 specific mistakes to avoid (skip tests, violate patterns, change API contracts, etc.).

---

### Lesson 7: Reference Existing Patterns
**What Happened:** Phase 11 constantly referenced VPR handler and logic patterns.

**What We Learned:** Reusing existing patterns ensures consistency and speeds up implementation.

**Application to Phase 9:** Reference VPR, Gap Analysis, and any other existing handlers/logic files.

---

### Lesson 8: Verification Commands for Each Phase
**What Happened:** Phase 11 provided exact commands for RED tests, GREEN tests, coverage checks, format, lint, type-check.

**What We Learned:** Exact verification commands remove ambiguity and ensure Engineer runs the right checks.

**Application to Phase 9:** Include the same comprehensive verification commands in ENGINEER_PROMPT.md.

---

### Lesson 9: Architecture Decisions Must Be Explicit
**What Happened:** Phase 11 documented synchronous vs async, LLM model, timeout, scoring algorithm, max questions.

**What We Learned:** Explicit architectural decisions prevent Engineer from making inconsistent choices.

**Application to Phase 9:** Document ALL architectural decisions in CV_TAILORING_DESIGN.md before creating task files.

---

### Lesson 10: Test-to-Task Mapping is Essential
**What Happened:** Phase 11 included a table mapping each task to its corresponding test file(s) and expected test count.

**What We Learned:** Clear mapping ensures every task has test coverage and prevents missed tests.

**Application to Phase 9:** Create the same Test-to-Task Mapping table in README.md.

---

## 🎯 PHASE 9 EXECUTION CHECKLIST

Use this checklist to track your progress:

### Gate 1: Architecture & Design ⏸️
- [ ] Create `docs/architecture/CV_TAILORING_DESIGN.md`
- [ ] Document CV tailoring algorithm
- [ ] Document relevance scoring system
- [ ] Document content prioritization strategy
- [ ] Document FVS integration approach
- [ ] Create data flow diagram
- [ ] Document LLM prompt strategy
- [ ] Make architectural decisions (sync/async, model, timeout, scoring, storage)

### Gate 2: Specification ⏸️
- [ ] Create `docs/specs/cv-tailoring/CV_TAILORING_SPEC.md`
- [ ] Define API endpoint (POST /api/cv-tailoring)
- [ ] Define request model (TailorCVRequest)
- [ ] Define response model (TailoredCV Response)
- [ ] Define result codes (CV_TAILORED_SUCCESS, etc.)
- [ ] Define error handling strategy
- [ ] Define authentication and authorization
- [ ] Define rate limiting
- [ ] Create OpenAPI schema

### Gate 3: Task Breakdown ⏸️
- [ ] Create `docs/tasks/09-cv-tailoring/README.md`
- [ ] Create 9-12 atomic task files
- [ ] Task 01: Validation utilities
- [ ] Task 02: Infrastructure (CDK)
- [ ] Task 03: Tailoring logic
- [ ] Task 04: Tailoring prompt
- [ ] Task 05: FVS integration
- [ ] Task 06: Tailoring handler
- [ ] Task 07: DAL extensions (OPTIONAL)
- [ ] Task 08: Pydantic models
- [ ] Task 09: Integration tests
- [ ] Task 10: E2E verification
- [ ] Task 11: Deployment
- [ ] Create Test-to-Task Mapping table

### Gate 4: Test Suite (RED Phase) ⏸️
- [ ] Create `tests/cv-tailoring/conftest.py` (20+ fixtures)
- [ ] Create `tests/cv-tailoring/unit/test_validation.py` (15-20 tests)
- [ ] Create `tests/cv-tailoring/unit/test_tailoring_logic.py` (25-30 tests)
- [ ] Create `tests/cv-tailoring/unit/test_tailoring_prompt.py` (15-20 tests)
- [ ] Create `tests/cv-tailoring/unit/test_fvs_integration.py` (20-25 tests)
- [ ] Create `tests/cv-tailoring/unit/test_tailoring_handler_unit.py` (15-20 tests)
- [ ] Create `tests/cv-tailoring/unit/test_tailoring_dal_unit.py` (10-15 tests, OPTIONAL)
- [ ] Create `tests/cv-tailoring/unit/test_tailoring_models.py` (20-25 tests)
- [ ] Create `tests/cv-tailoring/integration/test_tailoring_handler_integration.py` (25-30 tests)
- [ ] Create `tests/cv-tailoring/infrastructure/test_cv_tailoring_stack.py` (10-15 tests)
- [ ] Create `tests/cv-tailoring/e2e/test_cv_tailoring_flow.py` (10-15 tests)
- [ ] Verify total test count: 150-200 tests
- [ ] Run RED tests: `uv run pytest tests/cv-tailoring/ -v --tb=short`
- [ ] Confirm ALL tests FAIL (no implementation exists)

### Gate 5: Handoff Documentation ⏸️
- [ ] Create `docs/tasks/09-cv-tailoring/ARCHITECT_SIGN_OFF.md`
  - [ ] Executive summary
  - [ ] Deliverables summary (all files listed)
  - [ ] Architecture decisions documented
  - [ ] Verification checklist
  - [ ] Handoff instructions
- [ ] Create `docs/tasks/09-cv-tailoring/ENGINEER_PROMPT.md`
  - [ ] Mission statement with CLAUDE.md rules
  - [ ] Pre-implementation reading checklist
  - [ ] Phase 0: RED test verification
  - [ ] Task-by-task implementation guide (9-12 tasks)
  - [ ] Test-after-each-task enforcement
  - [ ] Deployment guide
  - [ ] Completion checklist
  - [ ] Common pitfalls section (7-10 items)
  - [ ] Reference files section (links to all deliverables)

### Final Verification ⏸️
- [ ] Count total files created (target: 30-35 files)
- [ ] Count total lines of documentation/tests (target: 18,000-22,000 lines)
- [ ] Verify Test-to-Task Mapping is complete
- [ ] Verify all architectural decisions are documented
- [ ] Verify all verification commands are included
- [ ] Verify Engineer can implement without asking questions
- [ ] Run RED tests one final time to confirm all fail
- [ ] Create final sign-off certification

---

## 🚀 EXECUTION INSTRUCTIONS

1. **Read this prompt thoroughly.** Understand the scope, deliverables, and role boundaries.

2. **Research Phase 11.** Read all Phase 11 deliverables to understand the pattern:
   ```bash
   cat docs/architecture/GAP_ANALYSIS_DESIGN.md
   cat docs/specs/gap-analysis/GAP_SPEC.md
   cat docs/tasks/11-gap-analysis/ARCHITECT_SIGN_OFF.md
   cat docs/tasks/11-gap-analysis/ENGINEER_PROMPT.md
   ls -la tests/gap-analysis/
   ```

3. **Research existing patterns.** Scan VPR handler and logic for similar patterns:
   ```bash
   cat handlers/vpr_handler.py
   cat logic/vpr_generator.py
   cat dal/dynamo_dal_handler.py
   ```

4. **Execute Gates 1-5 sequentially.** Do NOT skip ahead. Complete each gate before moving to the next.

5. **Use the Execution Checklist.** Mark items as complete. Track your progress.

6. **Verify at each gate.** Use the verification commands to confirm completion.

7. **Stop after Gate 5.** Do NOT implement code. Your role ends when all documentation and tests are created.

8. **Certify handoff.** Create ARCHITECT_SIGN_OFF.md certifying that all architectural work is complete.

---

## 📞 QUESTIONS FOR USER (OPTIONAL)

If you need clarification on Phase 9 requirements, ask these questions BEFORE starting:

1. **Synchronous or Async?**
   - Should CV tailoring be synchronous (like VPR and Gap Analysis) or async (like future VPR phases)?
   - Recommendation: Synchronous for simplicity and consistency.

2. **LLM Model Choice?**
   - Should we use Claude Haiku 4.5 (fast, cheap) or Claude Sonnet 4.5 (better quality)?
   - Recommendation: Haiku for cost optimization, unless user wants premium quality.

3. **Storage Strategy?**
   - Should tailored CVs be stored as artifacts in DynamoDB with TTL?
   - Recommendation: Yes, with 90-day TTL (same as Phase 11).

4. **FVS Validation Strictness?**
   - Should FVS validation block tailored CV generation if facts cannot be verified?
   - Recommendation: Return validation results but allow generation to proceed.

5. **Tailoring Preferences?**
   - Should users be able to specify tone (formal/casual), length (1-page/2-page), or emphasis (skills/experience)?
   - Recommendation: Yes, make preferences optional with sensible defaults.

---

## ✅ SUCCESS CRITERIA

Your architectural work is COMPLETE when:

1. **All 30-35 files created:**
   - 2 architecture documents
   - 1 specification
   - 12 task documentation files (README + 11 tasks)
   - 15 test files (150-200 tests)
   - 2 handoff documents

2. **All architectural decisions documented:**
   - Synchronous vs async
   - LLM model choice
   - Timeout value
   - Relevance scoring algorithm
   - FVS integration approach
   - Storage strategy

3. **All tests fail (RED phase verified):**
   ```bash
   uv run pytest tests/cv-tailoring/ -v --tb=short
   # Expected: 150-200 tests FAIL
   ```

4. **Test-to-Task Mapping is complete:**
   - Every task has corresponding test file(s)
   - Expected test counts documented

5. **Engineer has comprehensive guidance:**
   - ENGINEER_PROMPT.md is detailed and unambiguous
   - Task files include pseudo-code and verification commands
   - Common pitfalls section prevents mistakes

6. **Handoff certification complete:**
   - ARCHITECT_SIGN_OFF.md certifies all deliverables
   - Next phase clearly defined (Implementation by Engineer)

---

## 🎖️ ARCHITECT CERTIFICATION TEMPLATE

When you complete all work, create `ARCHITECT_SIGN_OFF.md` with this template:

```markdown
# Phase 9 CV Tailoring - Architect Sign-Off

**Date:** [DATE]
**Architect:** Claude Sonnet 4.5
**Status:** ✅ COMPLETE - Ready for Engineer Implementation

---

## Executive Summary

All architectural work for Phase 9 CV Tailoring is **COMPLETE**. The Engineer (Minimax) has comprehensive documentation, task breakdown, and a complete test suite (RED phase) to begin implementation.

---

## Deliverables Summary

### 1. Architecture Documentation ✅
- [x] `docs/architecture/CV_TAILORING_DESIGN.md` ([SIZE] bytes)
- [x] `docs/architecture/FVS_INTEGRATION.md` ([SIZE] bytes) (if created)

### 2. API Specification ✅
- [x] `docs/specs/cv-tailoring/CV_TAILORING_SPEC.md` ([SIZE] bytes)

### 3. Task Documentation ✅
- [x] `docs/tasks/09-cv-tailoring/README.md` ([SIZE] bytes)
- [x] Task 01: Validation utilities (task-01-validation.md)
- [x] Task 02: Infrastructure (task-02-infrastructure.md)
- [x] Task 03: Tailoring logic (task-03-tailoring-logic.md)
- [x] Task 04: Tailoring prompt (task-04-tailoring-prompt.md)
- [x] Task 05: FVS integration (task-05-fvs-integration.md)
- [x] Task 06: Tailoring handler (task-06-tailoring-handler.md)
- [x] Task 07: DAL extensions (task-07-dal-extensions.md) - OPTIONAL
- [x] Task 08: Pydantic models (task-08-models.md)
- [x] Task 09: Integration tests (task-09-integration-tests.md)
- [x] Task 10: E2E verification (task-10-e2e-verification.md)
- [x] Task 11: Deployment (task-11-deployment.md)

**Total:** [NUMBER] task documentation files

### 4. Complete Test Suite (RED Phase) ✅

**Total Test Files:** [NUMBER] files
**Total Test Cases:** [NUMBER] tests

[List all test files with test counts]

---

## Architecture Decisions

[Document all key decisions made]

---

## Verification Checklist

### Architectural Work (Architect Responsibilities) ✅

- [x] All design documents created
- [x] All specifications created
- [x] All task documentation created
- [x] Complete test suite created
- [x] Unit test for each task
- [x] Integration test coverage
- [x] Infrastructure test coverage
- [x] E2E test coverage
- [x] Follows Layered Monarchy pattern
- [x] Follows Result[T] pattern
- [x] Follows existing patterns (VPR, Gap Analysis)
- [x] Security requirements documented
- [x] Observability requirements documented
- [x] FVS integration requirements documented

**Total Files Created:** [NUMBER] files
**Total Lines of Documentation/Tests:** ~[NUMBER] lines

---

## Handoff to Engineer

**Engineer (Minimax):** You have everything needed to begin TDD implementation.

[Include start here instructions]

---

## Critical Reminders for Engineer

[List all critical rules and patterns to follow]

---

## Architect Sign-Off

**Architect Certification:**

I certify that all architectural work for Phase 9 CV Tailoring is complete and ready for implementation. The Engineer has:
- Comprehensive design documentation
- Detailed task breakdown with implementation guidance
- Complete test suite (RED phase)
- Clear success criteria and verification commands

**Status:** ✅ ARCHITECTURE COMPLETE
**Next Phase:** Implementation (Engineer responsibility)
**Estimated Implementation Time:** [HOURS] hours (per task estimates)

---

**Signed:**
Claude Sonnet 4.5 (Lead Architect)
[DATE]
```

---

## 🏁 CONCLUSION

You are now ready to architect Phase 9: CV Tailoring. Follow this prompt exactly, use Phase 11 as your model, and create comprehensive documentation and tests for the Engineer to implement.

**Remember:**
- You are the Architect ONLY (no implementation)
- TDD workflow: Design → Spec → Tasks → Tests (RED) → STOP
- Test-after-each-task enforcement in Engineer prompt
- Reference existing patterns (VPR, Gap Analysis)
- Make all architectural decisions explicit
- Create handoff documentation (ARCHITECT_SIGN_OFF.md, ENGINEER_PROMPT.md)

**Good luck, Architect. Build something great.**

---

**End of Architect Prompt**
