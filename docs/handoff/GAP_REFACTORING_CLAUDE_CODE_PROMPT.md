# Claude Code Prompt: Gap Analysis Integration Refactoring

**Context File:** `/docs/architecture/GAP_ANALYSIS_REFACTORING_PLAN.md`
**Output Directory:** `/docs/specs/gap-analysis/`, `/docs/tasks/11-gap-analysis/`, `/docs/tasks/09-cv-tailoring/`, `/docs/tasks/10-cover-letter/`, `/tests/`
**Objective:** Generate complete specifications, tasks, tests, and GitHub workflows for Gap Analysis integration

---

## MISSION

You are the Lead Architect for CareerVP. Your mission is to generate **COMPLETE** architectural documentation for the Gap Analysis Integration refactoring. This includes specs, tasks, tests, and GitHub workflows. You must follow the 5-Gate TDD Methodology and provide enough detail that an Engineer can implement without asking questions.

---

## REFERENCE DOCUMENTS (READ FIRST)

1. **`/docs/architecture/GAP_ANALYSIS_REFACTORING_PLAN.md`** - This refactoring plan (MUST READ)
2. **`/docs/architecture/GAP_ANALYSIS_DESIGN.md`** - Gap Analysis architecture
3. **`/docs/architecture/CV_TAILORING_DESIGN.md`** - CV Tailoring architecture
4. **`/docs/architecture/COVER_LETTER_DESIGN.md`** - Cover Letter architecture
5. **`/docs/architecture/VPR_ASYNC_DESIGN.md`** - Async pattern for Gap Analysis
6. **`/docs/specs/gap-analysis/GAP_SPEC.md`** - Existing Gap Analysis spec (if exists)
7. **`/docs/tasks/11-gap-analysis/`** - Existing Gap Analysis tasks
8. **`/docs/tasks/09-cv-tailoring/`** - Existing CV Tailoring tasks
9. **`/docs/tasks/10-cover-letter/`** - Existing Cover Letter tasks
10. **`/src/backend/careervp/models/job.py`** - GapResponse model
11. **`/src/backend/careervp/models/vpr.py`** - VPRRequest model with gap_responses
12. **`/src/backend/careervp/dal/dynamo_dal_handler.py`** - Existing DAL pattern

---

## CRITICAL REQUIREMENTS

### 1. Gap Responses Integration

**Gap responses MUST flow through all artifacts:**

| Feature | Input | Output |
|---------|-------|--------|
| Gap Analysis | CV + Job Posting | Questions |
| User Response | Questions | GapResponses (CV_IMPACT, INTERVIEW_ONLY) |
| VPR | GapResponses | VPR with gap_strategies |
| CV Tailoring | GapResponses | Tailored CV with gap-derived bullet points |
| Cover Letter | GapResponses | Cover letter with gap-derived paragraphs |

**Model Definitions:**

```python
class GapResponse(BaseModel):
    """Already exists in models/job.py"""
    question_id: str
    question: str
    answer: str
    destination: Literal['CV_IMPACT', 'INTERVIEW_MVP_ONLY']
```

**DAL Methods Required:**

```python
class DynamoDalHandler:
    def save_gap_responses(
        self,
        application_id: str,
        user_id: str,
        job_id: str,
        responses: list[GapResponse]
    ) -> Result[None]:
        """Store gap responses. Key: PK=APPLICATION#{id}, SK=GAP_RESPONSES"""

    def get_gap_responses(
        self,
        application_id: str
    ) -> Result[list[GapResponse]]:
        """Retrieve gap responses for an application."""

    def delete_gap_responses(
        self,
        application_id: str
    ) -> Result[None]:
        """Delete gap responses (cleanup)."""
```

### 2. Async Pattern for Gap Analysis

**Pattern (per VPR_ASYNC_DESIGN.md):**

```
POST /api/gap-analysis/submit
  ├─> Create job record in DynamoDB
  ├─> Enqueue to SQS
  └─> 202 ACCEPTED { job_id }

SQS triggers gap_worker_handler.py
  ├─> Retrieve user CV from DAL
  ├─> Call generate_gap_questions() via LLM
  ├─> Store questions in S3
  ├─> Update job status to COMPLETED
  └─> Notify frontend (WebSocket/API)

GET /api/gap-analysis/status/{job_id}
  └─> 200 OK { status, result_url (if complete) }
```

**Timeout:** 600 seconds (10 minutes) for LLM question generation

### 3. CV Tailoring Gap Integration

**Request Model Addition:**

```python
class TailorCVRequest(BaseModel):
    user_id: str
    cv_id: str
    job_id: str
    job_posting: JobPosting
    gap_responses: list[GapResponse] = Field(default_factory=list)
    # ... existing fields
```

**Prompt Template Addition:**

```
## Gap Analysis Responses (CV IMPACT)
{{#each gap_responses}}
{{#if (eq destination "CV_IMPACT")}}
Q: {{question}}
A: {{answer}}
{{/if}}
{{/each}}

Use these responses to enhance bullet points with specific accomplishments.
```

### 4. Cover Letter Gap Integration

**Request Model Addition:**

```python
class GenerateCoverLetterRequest(BaseModel):
    cv_id: str
    job_id: str
    application_id: str
    company_name: str
    job_title: str
    gap_responses: list[GapResponse] = Field(default_factory=list)
    preferences: Optional[CoverLetterPreferences] = None
    # ... existing fields
```

**Prompt Template Addition:**

```
## Gap Analysis Responses
{{#each gap_responses}}
- Q: {{question}}
  A: {{answer}}
{{/each}}

Incorporate these responses into compelling narrative paragraphs.
```

---

## OUTPUT SPECIFICATIONS

### 1. Specifications (6 files)

Create/update these files in `/docs/specs/gap-analysis/`:

#### a. `GAP_SPEC.md` (Complete Rewrite)
- API endpoints (submit, status, submit-responses)
- Request/Response models (Pydantic)
- Data flow diagram
- Error handling
- Storage schema
- Security considerations

#### b. `CV_TAILORING_SPEC.md` (Update)
- Add gap_responses to TailorCVRequest
- Add gap_responses section to prompt strategy
- Update data flow diagram

#### c. `COVER_LETTER_SPEC.md` (Update)
- Add gap_responses to GenerateCoverLetterRequest
- Add gap_responses section to prompt strategy
- Update data flow diagram

#### d. `DAL_SPEC.md` (New)
- save_gap_responses() contract
- get_gap_responses() contract
- delete_gap_responses() contract
- DynamoDB schema
- Access patterns

#### e. `ASYNC_TASK_SPEC.md` (New)
- Generic async task pattern for Gap Analysis
- SQS queue configuration
- Worker handler pattern
- Status polling

#### f. `MODELS_SPEC.md` (New)
- All model definitions (GapAnalysisRequest, GapQuestion, GapAnalysisResponse, updated VPR, etc.)
- Field descriptions
- Validation rules

### 2. Tasks (New + Updates)

#### Gap Analysis Tasks (Update existing, add new)

Update in `/docs/tasks/11-gap-analysis/`:

| File | Update Required |
|------|-----------------|
| `task-01-async-foundation.md` | Ensure DAL methods included |
| `task-02-infrastructure.md` | Add SQS queue for gap_worker |
| `task-03-gap-analysis-logic.md` | Verify logic completeness |
| `task-04-gap-analysis-prompt.md` | Verify prompt completeness |
| `task-05-gap-handler.md` | Verify handler completeness |
| `task-06-dal-extensions.md` | **ADD**: save_gap_responses, get_gap_responses |
| `task-07-integration-tests.md` | Add gap response flow tests |

Add NEW:

| File | Content |
|------|---------|
| `task-08-gap-responses-dal.md` | DAL methods for gap responses |
| `task-09-vpr-gap-integration.md` | VPR retrieval + persistence |
| `task-10-gap-submit-handler.md` | Endpoint for submitting responses |

#### CV Tailoring Tasks (Update existing)

Update in `/docs/tasks/09-cv-tailoring/`:

| File | Update Required |
|------|-----------------|
| `task-03-tailoring-logic.md` | Add gap_responses to prompt |
| `task-04-tailoring-prompt.md` | Add gap_responses section |
| `task-05-tailoring-handler.md` | Add gap_responses retrieval |
| `task-08-models.md` | Add gap_responses to TailorCVRequest |

#### Cover Letter Tasks (Complete)

Complete in `/docs/tasks/10-cover-letter/`:

| File | Status | Content |
|------|--------|---------|
| `task-01-validation.md` | ✅ Exists | Keep as-is |
| `task-02-infrastructure.md` | Create | CDK for cover letter Lambda |
| `task-03-cover-letter-logic.md` | Create | Core logic with gap_responses |
| `task-04-cover-letter-prompt.md` | Create | Prompt with gap_responses |
| `task-05-fvs-integration.md` | Create | FVS validation |
| `task-06-cover-letter-handler.md` | Create | Lambda handler with gap_responses |
| `task-07-dal-extensions.md` | Create | Cover letter artifact storage |
| `task-08-models.md` | Create | GenerateCoverLetterRequest with gap_responses |
| `task-09-integration-tests.md` | Create | Full flow tests |
| `task-10-e2e-verification.md` | Create | E2E tests |
| `task-11-deployment.md` | Create | Deployment steps |

### 3. Test Files (New + Updates)

Create/update in `/tests/`:

#### Gap Analysis Tests

| File | Coverage |
|------|----------|
| `tests/gap-analysis/unit/test_gap_dal.py` | save_gap_responses, get_gap_responses, delete_gap_responses |
| `tests/gap-analysis/unit/test_gap_models.py` | Model validation |
| `tests/gap-analysis/unit/test_gap_submit_handler.py` | Submit endpoint |
| `tests/gap-analysis/unit/test_gap_worker_handler.py` | Worker processing |
| `tests/gap-analysis/integration/test_gap_flow.py` | Full async flow |
| `tests/gap-analysis/e2e/test_gap_e2e.py` | End-to-end test |

#### CV Tailoring Tests (Update)

| File | Update |
|------|--------|
| `tests/cv-tailoring/unit/test_tailoring_logic.py` | Add gap_responses tests |
| `tests/cv-tailoring/unit/test_tailoring_handler.py` | Add gap_responses retrieval tests |
| `tests/cv-tailoring/unit/test_tailoring_prompt.py` | Add gap_responses prompt tests |

#### Cover Letter Tests (Create)

| File | Coverage |
|------|----------|
| `tests/cover-letter/unit/test_cover_letter_logic.py` | Core logic with gap_responses |
| `tests/cover-letter/unit/test_cover_letter_handler.py` | Handler with gap_responses |
| `tests/cover-letter/unit/test_cover_letter_prompt.py` | Prompt with gap_responses |
| `tests/cover-letter/unit/test_cover_letter_models.py` | Model validation |
| `tests/cover-letter/integration/test_cover_letter_flow.py` | Full flow |
| `tests/cover-letter/e2e/test_cover_letter_e2e.py` | E2E test |

#### Integration Tests

| File | Coverage |
|------|----------|
| `tests/integration/test_gap_to_artifacts.py` | Gap responses → VPR → CV → Cover Letter |
| `tests/integration/test_dal_gap_responses.py` | DAL operations |

#### Fixtures (Update)

Update `tests/conftest.py`:

```python
@pytest.fixture
def sample_gap_responses() -> list[GapResponse]:
    """Sample gap analysis responses."""
    return [
        GapResponse(
            question_id="gap_001",
            question="You worked as DevOps at Company X...",
            answer="I led a team of 5 engineers...",
            destination="CV_IMPACT"
        ),
        GapResponse(
            question_id="gap_002",
            question="Describe your experience with...",
            answer="I used AWS Lambda extensively...",
            destination="INTERVIEW_MVP_ONLY"
        )
    ]

@pytest.fixture
def sample_gap_analysis_request() -> GapAnalysisRequest:
    """Sample gap analysis request."""
    return GapAnalysisRequest(
        user_id="user_123",
        cv_id="cv_456",
        job_posting=sample_job_posting(),
        language="en"
    )
```

### 4. GitHub Workflows (New)

Create in `.github/workflows/`:

#### a. `gap-analysis-tests.yml`

```yaml
name: Gap Analysis Tests

on:
  push:
    paths:
      - 'src/backend/careervp/logic/gap_analysis.py'
      - 'src/backend/careervp/handlers/gap_*.py'
      - 'tests/gap-analysis/**'
  pull_request:
    paths:
      - 'src/backend/careervp/logic/gap_analysis.py'
      - 'src/backend/careervp/handlers/gap_*.py'
      - 'tests/gap-analysis/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd src/backend
          uv sync
      - name: Run gap-analysis tests
        run: uv run pytest tests/gap-analysis/ -v --cov=careervp --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

#### b. `cv-tailoring-gap-tests.yml`

```yaml
name: CV Tailoring Gap Tests

on:
  push:
    paths:
      - 'src/backend/careervp/logic/cv_tailor.py'
      - 'src/backend/careervp/handlers/cv_tailoring_handler.py'
      - 'tests/cv-tailoring/**'
  pull_request:
    paths:
      - 'src/backend/careervp/logic/cv_tailor.py'
      - 'src/backend/careervp/handlers/cv_tailoring_handler.py'
      - 'tests/cv-tailoring/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd src/backend
          uv sync
      - name: Run CV tailoring tests
        run: uv run pytest tests/cv-tailoring/ -v --cov=careervp --cov-report=xml
```

#### c. `cover-letter-tests.yml`

```yaml
name: Cover Letter Tests

on:
  push:
    paths:
      - 'src/backend/careervp/logic/cover_letter_generator.py'
      - 'src/backend/careervp/handlers/cover_letter_handler.py'
      - 'tests/cover-letter/**'
  pull_request:
    paths:
      - 'src/backend/careervp/logic/cover_letter_generator.py'
      - 'src/backend/careervp/handlers/cover_letter_handler.py'
      - 'tests/cover-letter/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd src/backend
          uv sync
      - name: Run cover letter tests
        run: uv run pytest tests/cover-letter/ -v --cov=careervp --cov-report=xml
```

#### d. `integration-tests.yml`

```yaml
name: Integration Tests

on:
  push:
    paths:
      - 'tests/integration/**'
  pull_request:
    paths:
      - 'tests/integration/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd src/backend
          uv sync
      - name: Run integration tests
        run: uv run pytest tests/integration/ -v --cov=careervp --cov-report=xml
```

---

## CODE QUALITY STANDARDS

### Python Style

- **Formatting:** `ruff format`
- **Linting:** `ruff check --fix`
- **Type Checking:** `mypy --strict`
- **Docstrings:** Google style
- **Imports:** Sorted, no unused

### Test Standards

- **Coverage Target:** 90%+ for unit tests, 85%+ for integration tests
- **Test Naming:** `test_<module>_<function>_<scenario>.py`
- **Fixtures:** Use `conftest.py` for shared fixtures
- **Mocking:** Mock external dependencies (LLM, DynamoDB)
- **Parameterized:** Use `@pytest.mark.parametrize` for multiple scenarios

### Documentation Standards

- **Specs:** Include API contracts, data flow diagrams, examples
- **Tasks:** Include pseudo-code, verification commands, acceptance criteria
- **Comments:** Explain "why", not "what"
- **README:** Update for new features

---

## VERIFICATION COMMANDS

After generating all files, run these to verify:

```bash
cd src/backend

# Format
uv run ruff format .

# Lint
uv run ruff check --fix .

# Type check
uv run mypy careervp --strict

# Gap analysis tests
uv run pytest tests/gap-analysis/ -v --tb=short

# CV tailoring tests
uv run pytest tests/cv-tailoring/ -v --tb=short

# Cover letter tests
uv run pytest tests/cover-letter/ -v --tb=short

# Integration tests
uv run pytest tests/integration/ -v --tb=short

# Coverage report
uv run pytest tests/ --cov=careervp --cov-report=term-missing
```

---

## OUTPUT CHECKLIST

### Specs (6 files)
- [ ] `docs/specs/gap-analysis/GAP_SPEC.md`
- [ ] `docs/specs/gap-analysis/CV_TAILORING_SPEC.md` (update)
- [ ] `docs/specs/gap-analysis/COVER_LETTER_SPEC.md` (update)
- [ ] `docs/specs/gap-analysis/DAL_SPEC.md`
- [ ] `docs/specs/gap-analysis/ASYNC_TASK_SPEC.md`
- [ ] `docs/specs/gap-analysis/MODELS_SPEC.md`

### Gap Analysis Tasks (3 files)
- [ ] `docs/tasks/11-gap-analysis/task-08-gap-responses-dal.md`
- [ ] `docs/tasks/11-gap-analysis/task-09-vpr-gap-integration.md`
- [ ] `docs/tasks/11-gap-analysis/task-10-gap-submit-handler.md`

### CV Tailoring Tasks (4 files)
- [ ] `docs/tasks/09-cv-tailoring/task-03-tailoring-logic.md` (update)
- [ ] `docs/tasks/09-cv-tailoring/task-04-tailoring-prompt.md` (update)
- [ ] `docs/tasks/09-cv-tailoring/task-05-tailoring-handler.md` (update)
- [ ] `docs/tasks/09-cv-tailoring/task-08-models.md` (update)

### Cover Letter Tasks (10 files)
- [ ] `docs/tasks/10-cover-letter/task-02-infrastructure.md`
- [ ] `docs/tasks/10-cover-letter/task-03-cover-letter-logic.md`
- [ ] `docs/tasks/10-cover-letter/task-04-cover-letter-prompt.md`
- [ ] `docs/tasks/10-cover-letter/task-05-fvs-integration.md`
- [ ] `docs/tasks/10-cover-letter/task-06-cover-letter-handler.md`
- [ ] `docs/tasks/10-cover-letter/task-07-dal-extensions.md`
- [ ] `docs/tasks/10-cover-letter/task-08-models.md`
- [ ] `docs/tasks/10-cover-letter/task-09-integration-tests.md`
- [ ] `docs/tasks/10-cover-letter/task-10-e2e-verification.md`
- [ ] `docs/tasks/10-cover-letter/task-11-deployment.md`

### Test Files (15 files)
- [ ] `tests/gap-analysis/unit/test_gap_dal.py`
- [ ] `tests/gap-analysis/unit/test_gap_models.py`
- [ ] `tests/gap-analysis/unit/test_gap_submit_handler.py`
- [ ] `tests/gap-analysis/unit/test_gap_worker_handler.py`
- [ ] `tests/gap-analysis/integration/test_gap_flow.py`
- [ ] `tests/gap-analysis/e2e/test_gap_e2e.py`
- [ ] `tests/cv-tailoring/unit/test_tailoring_logic.py` (update)
- [ ] `tests/cv-tailoring/unit/test_tailoring_handler.py` (update)
- [ ] `tests/cv-tailoring/unit/test_tailoring_prompt.py` (update)
- [ ] `tests/cover-letter/unit/test_cover_letter_logic.py`
- [ ] `tests/cover-letter/unit/test_cover_letter_handler.py`
- [ ] `tests/cover-letter/unit/test_cover_letter_prompt.py`
- [ ] `tests/cover-letter/unit/test_cover_letter_models.py`
- [ ] `tests/cover-letter/integration/test_cover_letter_flow.py`
- [ ] `tests/cover-letter/e2e/test_cover_letter_e2e.py`
- [ ] `tests/integration/test_gap_to_artifacts.py`
- [ ] `tests/integration/test_dal_gap_responses.py`
- [ ] `tests/conftest.py` (update)

### GitHub Workflows (4 files)
- [ ] `.github/workflows/gap-analysis-tests.yml`
- [ ] `.github/workflows/cv-tailoring-gap-tests.yml`
- [ ] `.github/workflows/cover-letter-tests.yml`
- [ ] `.github/workflows/integration-tests.yml`

---

## LESSONS LEARNED FROM PREVIOUS PHASES

### From CV Tailoring (Phase 9)

1. **Complete Test Suite = 150-200+ Tests**
   - Don't claim complete with only partial tests
   - Create ALL test files before marking complete

2. **Test-After-Each-Task Enforcement**
   - Engineers must run tests after EVERY task
   - Include verification commands

3. **Comprehensive Handoff Documentation**
   - 1,500+ lines of guidance
   - 50+ verification commands
   - Common pitfalls with solutions

### From Cover Letter (Phase 10)

1. **Tasks Must Be Complete Before Implementation**
   - Partial task sets cause confusion
   - Create all tasks upfront

---

## FINAL OUTPUT

Generate all files according to this prompt. After generation, provide:

1. **Summary:** List of all files created/updated
2. **Verification:** Results of running format/lint/type-check commands
3. **Gaps:** Any issues discovered during generation that need architect review
4. **Next Steps:** Recommended implementation order

---

**Prompt Version:** 1.0
**Created:** 2026-02-05
**Context File:** `/docs/architecture/GAP_ANALYSIS_REFACTORING_PLAN.md`
