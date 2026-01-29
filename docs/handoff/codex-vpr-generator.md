# Codex Handoff: VPR Generator Implementation

## Mission

Implement the Value Proposition Report (VPR) Generator for CareerVP. The VPR is a strategic document that maps a candidate's CV facts to job requirements, serving as the foundation for CV tailoring, cover letters, and interview prep.

## Critical Context

### Architecture Pattern

```
Handler (Lambda) → Logic (Business Rules) → DAL (DynamoDB)
```

All layers use the `Result[T]` pattern for error propagation. **No naked exceptions.**

### FVS (Fact Verification System) - MANDATORY

The VPR synthesizes data from **multiple sources**:

| Tier | Fields | Rule |
| ---- | ------ | ---- |
| **IMMUTABLE** | Dates, company names, job titles, contact info | NEVER modify or fabricate |
| **VERIFIABLE** | Skills, achievements | Must exist in source CV or gap_responses |
| **FLEXIBLE** | Executive summary, strategic framing | Creative liberty allowed |

**Source-code comments required:** Add `# FVS_COMMENT:` where IMMUTABLE fields are validated.

### LLM Model Selection

- **VPR Generation:** Claude Sonnet 4.5 (`TaskMode.STRATEGIC`)
- **Cost Target:** < $0.04 per VPR (~8K input, ~2.5K output tokens)
- **Timeout:** 120 seconds

---

## Implementation Order

Execute tasks in this exact sequence:

### Task 1: Models (COMPLETED)

Files created:
- `src/backend/careervp/models/job.py` ✓
- `src/backend/careervp/models/vpr.py` ✓

**Action Required:** Commit the models.

```bash
cd /Users/yitzchak/Documents/dev/careervp
git add src/backend/careervp/models/job.py src/backend/careervp/models/vpr.py
git commit -m "feat(vpr): add JobPosting and VPR Pydantic models"
```

### Task 2: DAL Methods

**File:** `src/backend/careervp/dal/dynamo_dal_handler.py`

Add these methods following the existing `save_cv`/`get_cv` patterns:

1. `save_vpr(vpr: VPR) -> None`
2. `get_vpr(application_id: str, version: int | None = None) -> VPR | None`
3. `get_latest_vpr(application_id: str) -> VPR | None`
4. `list_vprs(user_id: str) -> list[VPR]`

**DynamoDB Schema:**
- PK: `application_id`
- SK: `ARTIFACT#VPR#v{version}`
- GSI: `user_id` (for list queries)

**Reference:** `docs/tasks/03-vpr-generator/task-02-dal-methods.md`

### Task 3: Generator Logic

**File:** `src/backend/careervp/logic/vpr_generator.py`

Core function signature:

```python
def generate_vpr(
    request: VPRRequest,
    user_cv: UserCV,
    dal: DynamoDalHandler,
) -> Result[VPRResponse]:
```

**Must include:**
- Prompt building (from Task 4)
- LLM invocation via `LLMClient(TaskMode.STRATEGIC)`
- Response parsing to `VPR` model
- FVS validation against `user_cv`
- Token usage tracking

**Reference:** `docs/tasks/03-vpr-generator/task-03-generator-logic.md`

### Task 4: Prompt Integration

**File:** `src/backend/careervp/logic/prompts/vpr_prompt.py`

**IMPORTANT:** Extract `VPR_GENERATION_PROMPT` from existing Prompt Library:
- Source: `docs/features/CareerVP Prompt Library.md` (lines 128-259)
- Do NOT recreate the prompt - extract verbatim

**Functions:**
- `build_vpr_prompt(user_cv: UserCV, request: VPRRequest) -> str`
- `check_anti_ai_patterns(content: str) -> list[str]`

**Reference:** `docs/tasks/03-vpr-generator/task-04-sonnet-prompt.md`

### Task 5: Lambda Handler

**File:** `src/backend/careervp/handlers/vpr_handler.py`

Follow the pattern from `cv_upload_handler.py`:
- Powertools decorators: `@logger`, `@tracer`, `@metrics`
- Parse `VPRRequest` from event body
- Fetch user CV from DAL
- Call `generate_vpr()` logic
- Return `VPRResponse` as JSON

**HTTP Status Mapping:**
| Result Code | HTTP Status |
| ----------- | ----------- |
| VPR_GENERATED | 200 |
| INVALID_INPUT | 400 |
| CV not found | 404 |
| FVS_HALLUCINATION_DETECTED | 422 |
| LLM_API_ERROR | 502 |

**Reference:** `docs/tasks/03-vpr-generator/task-05-handler.md`

### Task 6: Unit Tests

**Files:**
- `tests/unit/test_vpr_generator.py`
- `tests/unit/test_vpr_handler.py`
- `tests/unit/test_vpr_prompt.py`

**Mocking:**
- Use `moto` for DynamoDB
- Use `unittest.mock.patch` for `LLMClient`
- NEVER call real APIs

**Coverage Targets:**
- `vpr_generator.py`: 90%+
- `vpr_handler.py`: 85%+

**Reference:** `docs/tasks/03-vpr-generator/task-06-tests.md`

---

## Mandatory Validation Commands

Run these after EVERY file modification:

```bash
# Linting
cd src/backend && uv run ruff format <file>
cd src/backend && uv run ruff check --fix <file>

# Type checking
cd src/backend && uv run mypy <file> --strict

# Tests (after implementation)
cd src/backend && uv run pytest tests/unit/test_vpr*.py -v
```

**Zero errors required before marking any checkbox complete.**

---

## Key Files to Read First

1. **Spec:** `docs/specs/03-vpr-generator.md`
2. **Rules:** `.clauderules` and `AGENTS.md`
3. **Prompt Library:** `docs/features/CareerVP Prompt Library.md`
4. **Existing Patterns:**
   - `src/backend/careervp/handlers/cv_upload_handler.py`
   - `src/backend/careervp/dal/dynamo_dal_handler.py`
   - `src/backend/careervp/logic/fvs_validator.py`
   - `src/backend/careervp/models/result.py`

---

## Anti-Patterns to Avoid

1. **DO NOT** raise naked exceptions - always return `Result` objects
2. **DO NOT** fabricate dates, companies, or job titles not in the CV
3. **DO NOT** call real LLM APIs in tests
4. **DO NOT** skip mypy --strict checks
5. **DO NOT** modify IMMUTABLE fields from user_cv
6. **DO NOT** recreate prompts that exist in Prompt Library

---

## Success Criteria

- [ ] All 6 tasks completed with checkboxes marked
- [ ] `uv run pytest tests/unit/test_vpr*.py -v` passes
- [ ] `uv run mypy src/backend/careervp --strict` passes
- [ ] `uv run ruff check src/backend/careervp` shows zero errors
- [ ] VPR generation works end-to-end (mocked LLM)
- [ ] FVS validation blocks hallucinated dates/companies

---

## Quick Start

```bash
# Navigate to project
cd /Users/yitzchak/Documents/dev/careervp

# Read the spec first
cat docs/specs/03-vpr-generator.md

# Check current task status
cat docs/tasks/03-vpr-generator/task-01-models.md

# Begin with Task 1 commit, then proceed to Task 2
```
