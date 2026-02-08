# Phase 10: Cover Letter Generation - Engineer Implementation Prompt

**Date:** 2026-02-06
**Phase:** 10 - Cover Letter Generation
**Status:** Ready for Implementation
**Total Duration:** 19 hours | 11 tasks | 165-216 tests

---

## TABLE OF CONTENTS

1. [Quick Start](#part-1-quick-start)
2. [CLAUDE.md Rules](#part-2-claudemd-rules-mandatory)
3. [Pre-Implementation Reading List](#part-3-pre-implementation-reading-list)
4. [Task-by-Task Implementation Guide](#part-4-task-by-task-implementation-guide)
5. [Common Pitfalls](#part-5-common-pitfalls)
6. [Verification Commands](#part-6-verification-commands)
7. [Reference Implementation Examples](#part-7-reference-implementation-examples)

---

# PART 1: QUICK START

## Phase Overview

Phase 10 implements an intelligent cover letter generation engine that synthesizes:
- User's Value Proposition Report (VPR)
- Master CV and optionally tailored CV
- Gap analysis responses
- Company research

Into a personalized, anti-AI-detection-optimized cover letter using Claude Haiku 4.5.

### Success Metrics
- Quality Score: Average >= 0.75 across all generated cover letters
- Latency: p95 response time < 20 seconds
- Cost: Average cost per letter < $0.006
- FVS Compliance: 100% of company names and job titles verified

## File Structure to Create

```
src/backend/careervp/
├── handlers/
│   ├── cover_letter_handler.py          # Task 06
│   └── utils/
│       └── validation.py                 # Task 01 (extend existing)
├── logic/
│   ├── cover_letter_generator.py         # Task 03
│   ├── fvs_cover_letter.py               # Task 05
│   └── prompts/
│       └── cover_letter_prompt.py        # Task 04
├── models/
│   └── cover_letter_models.py            # Task 08
└── dal/
    └── dynamo_dal_handler.py             # Task 07 (extend existing)

tests/cover-letter/
├── __init__.py
├── conftest.py                           # Fixtures (20+)
├── unit/
│   ├── __init__.py
│   ├── test_validation.py                # Task 01 (19 tests)
│   ├── test_cover_letter_logic.py        # Task 03 (27 tests)
│   ├── test_cover_letter_prompt.py       # Task 04 (16 tests)
│   ├── test_fvs_integration.py           # Task 05 (24 tests)
│   ├── test_cover_letter_handler_unit.py # Task 06 (19 tests)
│   ├── test_cover_letter_dal_unit.py     # Task 07 (14 tests)
│   └── test_cover_letter_models.py       # Task 08 (27 tests)
├── integration/
│   ├── __init__.py
│   └── test_cover_letter_handler_integration.py  # Task 09 (22 tests)
├── infrastructure/
│   ├── __init__.py
│   └── test_cover_letter_stack.py        # Task 02 (28 tests)
└── e2e/
    ├── __init__.py
    └── test_cover_letter_flow.py         # Task 10 (20 tests)
```

## Quick Verification Commands

```bash
# Navigate to backend
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format all cover letter code
uv run ruff format careervp/

# Lint all cover letter code
uv run ruff check --fix careervp/

# Type check all cover letter code
uv run mypy careervp --strict

# Run all cover letter tests
uv run pytest tests/cover-letter/ -v --cov=careervp --cov-report=html

# Expected: 216 tests PASS, coverage >= 90%
```

---

# PART 2: CLAUDE.MD RULES (MANDATORY)

Before writing ANY code, internalize these 10 critical rules from CLAUDE.md:

## RULE 1: Layered Monarchy - Handler -> Logic -> DAL

**Pattern:** Handler calls Logic, Logic calls DAL. Never skip layers.

```python
# CORRECT
# cover_letter_handler.py
from careervp.logic.cover_letter_generator import generate_cover_letter
result = await generate_cover_letter(request, user_id, llm_client, dal)

# WRONG - Handler directly accessing DAL
# from careervp.dal.dynamo_dal_handler import DynamoDalHandler
# dal = DynamoDalHandler()
# cv = dal.get_cv(cv_id)  # WRONG: Logic layer skipped
```

**Verification:** Every handler imports from `careervp.logic.*`, never from `careervp.dal.*` directly for business operations.

---

## RULE 2: Result[T] Pattern - All Logic Functions Return Result

**Pattern:** Every logic function returns `Result[T]` with success/error/code.

```python
from careervp.models.result import Result, ResultCode

async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    user_id: str,
    llm_client: LLMClient,
    dal: DynamoDalHandler,
) -> Result[TailoredCoverLetter]:
    """Generate personalized cover letter."""
    try:
        # Success case
        return Result.success(
            data=cover_letter,
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
        )
    except Exception as e:
        # Error case
        return Result.failure(
            error=str(e),
            code=ResultCode.INTERNAL_ERROR,
        )
```

**Verification:** Run `grep -r "def.*:" careervp/logic/ | grep -v "Result\["` - should return nothing for business logic functions.

---

## RULE 3: Pydantic Validation - All Request/Response Models

**Pattern:** Use Pydantic BaseModel for all API contracts.

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class GenerateCoverLetterRequest(BaseModel):
    cv_id: str = Field(..., min_length=1, max_length=255)
    job_id: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    job_title: str = Field(..., min_length=1, max_length=255)
    preferences: Optional[CoverLetterPreferences] = None

class CoverLetterPreferences(BaseModel):
    tone: Literal["professional", "enthusiastic", "technical"] = "professional"
    word_count_target: int = Field(default=300, ge=200, le=500)
    emphasis_areas: Optional[list[str]] = None
```

**Verification:** Every request/response uses Pydantic with Field validators.

---

## RULE 4: AWS Powertools - @logger, @tracer, @metrics Decorators

**Pattern:** All handlers MUST have observability decorators.

```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Handle cover letter generation request."""
    # Implementation
```

**Verification:** Every handler file has all three decorators on `lambda_handler`.

---

## RULE 5: FVS Integration - VERIFIABLE for Company/Job, FLEXIBLE for Content

**Pattern:** Cover letters have three FVS tiers:
- **IMMUTABLE:** None (cover letters are creative content)
- **VERIFIABLE:** Company name, job title (must match exactly)
- **FLEXIBLE:** All narrative content (full creative liberty)

```python
def validate_cover_letter(
    content: str,
    baseline: FVSBaseline,
) -> FVSValidationResult:
    """Validate cover letter against FVS baseline.

    CRITICAL violations: Company name completely wrong
    WARNING violations: Job title partially matched
    """
    # Company name must match (CRITICAL if missing)
    if baseline.company_name.lower() not in content.lower():
        violations.append(FVSViolation(
            field="company_name",
            severity="critical",
            message=f"Company '{baseline.company_name}' not found",
        ))

    return FVSValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
    )
```

**Verification:** `validate_cover_letter()` MUST be called before returning any generated cover letter.

---

## RULE 6: TDD Workflow - Tests Exist, Make Them Pass

**Pattern:** Tests are pre-written. Your job is to make them GREEN.

```bash
# Before starting each task, verify tests FAIL (RED)
cd src/backend
uv run pytest tests/cover-letter/unit/test_validation.py -v
# Expected: ModuleNotFoundError or assertion failures

# After implementing, tests should PASS (GREEN)
uv run pytest tests/cover-letter/unit/test_validation.py -v
# Expected: 19 tests PASSED
```

**Verification:** Run tests IMMEDIATELY after completing each task. Do NOT batch.

---

## RULE 7: Timeout Handling - 300s Lambda, asyncio.wait_for

**Pattern:** All LLM calls use asyncio.wait_for with 300-second timeout.

```python
import asyncio

async def generate_cover_letter(...) -> Result[TailoredCoverLetter]:
    try:
        llm_response = await asyncio.wait_for(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task_mode=TaskMode.TEMPLATE,
                model="claude-haiku-4-5",
            ),
            timeout=300.0,  # 5 minutes
        )
    except asyncio.TimeoutError:
        return Result.failure(
            error="Cover letter generation timed out after 300s",
            code=ResultCode.CV_LETTER_GENERATION_TIMEOUT,
        )
```

**Verification:** Every LLM call wrapped in `asyncio.wait_for(...)`.

---

## RULE 8: Error Mapping - ResultCode to HTTP Status

**Pattern:** Consistent mapping from result codes to HTTP status codes.

```python
RESULT_CODE_TO_HTTP_STATUS = {
    ResultCode.COVER_LETTER_GENERATED_SUCCESS: 200,
    ResultCode.CV_NOT_FOUND: 404,
    ResultCode.JOB_NOT_FOUND: 404,
    ResultCode.VPR_NOT_FOUND: 400,
    ResultCode.FVS_HALLUCINATION_DETECTED: 400,
    ResultCode.CV_LETTER_GENERATION_TIMEOUT: 504,
    ResultCode.RATE_LIMIT_EXCEEDED: 429,
    ResultCode.INVALID_REQUEST: 400,
    ResultCode.UNAUTHORIZED: 401,
    ResultCode.FORBIDDEN: 403,
    ResultCode.INTERNAL_ERROR: 500,
}

def get_http_status(code: ResultCode) -> int:
    return RESULT_CODE_TO_HTTP_STATUS.get(code, 500)
```

**Verification:** All result codes have HTTP status mappings.

---

## RULE 9: Quality Scoring - 40% Personalization + 35% Relevance + 25% Tone

**Pattern:** Quality score formula is FIXED and must sum to 1.0.

```python
# Quality score weights (MUST sum to 1.0)
PERSONALIZATION_WEIGHT = 0.40  # Specific accomplishments cited
RELEVANCE_WEIGHT = 0.35        # Job requirements addressed
TONE_WEIGHT = 0.25             # Matches requested tone

def calculate_overall_score(
    personalization: float,
    relevance: float,
    tone: float,
) -> float:
    return (
        PERSONALIZATION_WEIGHT * personalization +
        RELEVANCE_WEIGHT * relevance +
        TONE_WEIGHT * tone
    )

# Quality thresholds
QUALITY_EXCELLENT = 0.80  # Return immediately
QUALITY_GOOD = 0.70       # Acceptable
QUALITY_RETRY = 0.70      # Below this, retry with Sonnet
```

**Verification:** Check weights sum to 1.0: `0.40 + 0.35 + 0.25 = 1.00`

---

## RULE 10: Anti-AI Detection - Sentence Variation, No Buzzwords

**Pattern:** LLM prompts include anti-AI detection guidelines.

```python
ANTI_AI_GUIDELINES = """
CRITICAL WRITING GUIDELINES (Anti-AI Detection):
1. VARY sentence structure - mix short punchy sentences with longer ones
2. USE natural transitions - avoid "Furthermore", "Moreover", "Additionally"
3. AVOID buzzwords - no "synergy", "leverage", "innovative solutions"
4. INCLUDE specific details - numbers, dates, project names where possible
5. WRITE conversationally - use contractions occasionally ("I'm", "I've")
6. START sentences differently - don't begin multiple sentences with "I"
7. USE active voice predominantly
8. AVOID lists in cover letters - use flowing paragraphs
"""
```

**Verification:** System prompt includes all 8 anti-AI guidelines.

---

# PART 3: PRE-IMPLEMENTATION READING LIST

## Before Starting Task 01

Read these documents in order (estimated 45 minutes total):

### Architecture Documents (20 minutes)

| Document | Sections to Focus On | Location |
|----------|---------------------|----------|
| **COVER_LETTER_DESIGN.md** | Quality Scoring Algorithm, FVS Integration, Data Flow | `/docs/architecture/COVER_LETTER_DESIGN.md` |
| | Sections 4-6 cover the core algorithms | |

Key concepts from COVER_LETTER_DESIGN.md:
1. **Quality Score Formula:** `0.40 × personalization + 0.35 × relevance + 0.25 × tone`
2. **FVS Tiers:** VERIFIABLE (company/job), FLEXIBLE (content)
3. **LLM Model:** Claude Haiku 4.5 (TaskMode.TEMPLATE)
4. **Timeout:** 300 seconds via asyncio.wait_for()
5. **Storage:** DynamoDB with 90-day TTL

### Specification Documents (15 minutes)

| Document | Sections to Focus On | Location |
|----------|---------------------|----------|
| **COVER_LETTER_SPEC.md** | Request/Response Models, Result Codes, HTTP Status Mappings | `/docs/specs/cover-letter/COVER_LETTER_SPEC.md` |

Key concepts from COVER_LETTER_SPEC.md:
1. **Request Model:** GenerateCoverLetterRequest with cv_id, job_id, company_name, job_title
2. **Response Model:** TailoredCoverLetterResponse with cover_letter, quality_score, download_url
3. **Result Codes:** COVER_LETTER_GENERATED_SUCCESS, FVS_HALLUCINATION_DETECTED, etc.
4. **Rate Limits:** Free tier 5/min, Premium 15/min, Enterprise 50/min

### Task Overview (5 minutes)

| Document | Purpose | Location |
|----------|---------|----------|
| **README.md** | Task dependencies, ordering, test counts | `/docs/tasks/10-cover-letter/README.md` |

### Existing Code Patterns (5 minutes each)

| File | Pattern to Study | Location |
|------|------------------|----------|
| **cv_upload_handler.py** | Handler structure with Powertools | `/src/backend/careervp/handlers/cv_upload_handler.py` |
| **vpr_generator.py** | Logic layer with Result[T] pattern | `/src/backend/careervp/logic/vpr_generator.py` |
| **fvs_validator.py** | FVS validation pattern | `/src/backend/careervp/logic/fvs_validator.py` |
| **dynamo_dal_handler.py** | DAL pattern for DynamoDB | `/src/backend/careervp/dal/dynamo_dal_handler.py` |

---

# PART 4: TASK-BY-TASK IMPLEMENTATION GUIDE

## Implementation Order (Critical Path)

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

---

## TASK 01: Validation Utilities

**File:** `src/backend/careervp/handlers/utils/validation.py` (extend existing)
**Purpose:** Input validation functions for cover letter requests
**Complexity:** Low | **Duration:** 1 hour | **Tests:** 19

### Files to Create/Modify

```
src/backend/careervp/handlers/utils/validation.py  # Extend with cover letter validation
tests/cover-letter/unit/test_validation.py         # Create new
```

### Key Implementation Details

1. **Define Constants:**
```python
# Validation constants (from COVER_LETTER_SPEC.md)
MIN_COMPANY_NAME_LENGTH = 1
MAX_COMPANY_NAME_LENGTH = 255
MIN_JOB_TITLE_LENGTH = 1
MAX_JOB_TITLE_LENGTH = 255
MIN_WORD_COUNT_TARGET = 200
MAX_WORD_COUNT_TARGET = 500
DEFAULT_WORD_COUNT_TARGET = 300
MAX_JOB_DESCRIPTION_LENGTH = 50_000
VALID_TONES = ["professional", "enthusiastic", "technical"]
MAX_EMPHASIS_AREAS = 10
MAX_EMPHASIS_AREA_LENGTH = 100

# XSS prevention patterns
UNSAFE_PATTERNS = [
    "<script", "javascript:", "onerror", "onload", "onclick", "onmouseover"
]
```

2. **Implement CoverLetterValidationError:**
```python
@dataclass
class CoverLetterValidationError(Exception):
    error_code: str
    message: str
    field: str | None = None
    actual_value: str | None = None
    constraint: str | None = None
```

3. **Implement Validation Functions:**
```python
def validate_company_name(company_name: str) -> None:
    """Validate company name (1-255 chars, no XSS patterns)."""
    if not company_name or not company_name.strip():
        raise CoverLetterValidationError(
            error_code="INVALID_COMPANY_NAME",
            message="Company name is required",
            field="company_name",
        )
    if len(company_name) > MAX_COMPANY_NAME_LENGTH:
        raise CoverLetterValidationError(...)
    if _contains_unsafe_patterns(company_name):
        raise CoverLetterValidationError(...)

def validate_job_title(job_title: str) -> None:
    """Validate job title (1-255 chars, no XSS patterns)."""
    # Similar to validate_company_name

def validate_word_count_target(word_count: int) -> None:
    """Validate word count (200-500 range)."""
    if word_count < MIN_WORD_COUNT_TARGET:
        raise CoverLetterValidationError(...)
    if word_count > MAX_WORD_COUNT_TARGET:
        raise CoverLetterValidationError(...)

def validate_tone(tone: str) -> None:
    """Validate tone (professional/enthusiastic/technical)."""
    if tone not in VALID_TONES:
        raise CoverLetterValidationError(...)

def validate_emphasis_areas(areas: Optional[list[str]]) -> None:
    """Validate emphasis areas (optional, max 10 items)."""
    if areas is None:
        return
    if len(areas) > MAX_EMPHASIS_AREAS:
        raise CoverLetterValidationError(...)
    for i, area in enumerate(areas):
        if not area or not area.strip():
            raise CoverLetterValidationError(...)
        if _contains_unsafe_patterns(area):
            raise CoverLetterValidationError(...)

def validate_job_description(job_desc: Optional[str]) -> None:
    """Validate job description (optional, max 50k chars)."""
    if job_desc is None:
        return
    if len(job_desc) > MAX_JOB_DESCRIPTION_LENGTH:
        raise CoverLetterValidationError(...)

def _contains_unsafe_patterns(text: str) -> bool:
    """Check for XSS patterns."""
    text_lower = text.lower()
    return any(pattern in text_lower for pattern in UNSAFE_PATTERNS)
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format
uv run ruff format careervp/handlers/utils/validation.py

# Lint
uv run ruff check --fix careervp/handlers/utils/validation.py

# Type check
uv run mypy careervp/handlers/utils/validation.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_validation.py -v

# Expected: 19 tests PASSED
```

### Common Mistakes to Avoid

1. **Not stripping whitespace:** Check `not company_name.strip()` not just `not company_name`
2. **Missing XSS patterns:** Include all 6 patterns from UNSAFE_PATTERNS
3. **Case sensitivity for tone:** Enforce exact lowercase match

---

## TASK 08: Pydantic Models

**File:** `src/backend/careervp/models/cover_letter_models.py` (new)
**Purpose:** Define all request/response models for cover letter API
**Complexity:** Low | **Duration:** 1 hour | **Tests:** 27

### Files to Create

```
src/backend/careervp/models/cover_letter_models.py
tests/cover-letter/unit/test_cover_letter_models.py
```

### Key Implementation Details

1. **CoverLetterPreferences Model:**
```python
class CoverLetterPreferences(BaseModel):
    """User preferences for cover letter generation."""

    tone: Literal["professional", "enthusiastic", "technical"] = Field(
        default="professional",
        description="Tone of the cover letter",
    )
    word_count_target: int = Field(
        default=300,
        ge=200,
        le=500,
        description="Target word count (200-500)",
    )
    emphasis_areas: Optional[List[str]] = Field(
        default=None,
        description="Areas to emphasize (max 10)",
    )
    include_salary_expectations: bool = Field(
        default=False,
        description="Whether to include salary expectations",
    )

    @field_validator("emphasis_areas")
    @classmethod
    def validate_emphasis_areas(cls, v):
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 emphasis areas allowed")
        return v
```

2. **GenerateCoverLetterRequest Model:**
```python
class GenerateCoverLetterRequest(BaseModel):
    """Request model for cover letter generation."""

    cv_id: str = Field(..., min_length=1, max_length=255)
    job_id: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    job_title: str = Field(..., min_length=1, max_length=255)
    job_description: Optional[str] = Field(None, max_length=50000)
    preferences: Optional[CoverLetterPreferences] = None

    @field_validator("company_name", "job_title")
    @classmethod
    def validate_no_script_tags(cls, v: str) -> str:
        if "<script" in v.lower():
            raise ValueError("Invalid characters detected")
        return v.strip()
```

3. **TailoredCoverLetter Model:**
```python
class TailoredCoverLetter(BaseModel):
    """Model for generated cover letter."""

    cover_letter_id: str
    cv_id: str
    job_id: str
    user_id: str
    company_name: str
    job_title: str
    content: str
    word_count: int = Field(..., ge=0)
    personalization_score: float = Field(..., ge=0.0, le=1.0)
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    tone_score: float = Field(..., ge=0.0, le=1.0)
    generated_at: datetime

    @property
    def overall_quality_score(self) -> float:
        """Calculate weighted overall quality score."""
        return (
            0.40 * self.personalization_score +
            0.35 * self.relevance_score +
            0.25 * self.tone_score
        )
```

4. **TailoredCoverLetterResponse Model:**
```python
class TailoredCoverLetterResponse(BaseModel):
    """Response model for cover letter generation."""

    success: bool
    cover_letter: Optional[TailoredCoverLetter] = None
    fvs_validation: Optional[FVSValidationResultModel] = None
    quality_score: float = Field(..., ge=0.0, le=1.0)
    code: str
    processing_time_ms: int = Field(..., ge=0)
    cost_estimate: float = Field(..., ge=0.0)
    download_url: Optional[str] = None
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run ruff format careervp/models/cover_letter_models.py
uv run ruff check --fix careervp/models/cover_letter_models.py
uv run mypy careervp/models/cover_letter_models.py --strict
uv run pytest tests/cover-letter/unit/test_cover_letter_models.py -v

# Expected: 27 tests PASSED
```

### Common Mistakes to Avoid

1. **Wrong quality score formula:** Must be exactly 0.40 + 0.35 + 0.25 = 1.0
2. **Missing @field_validator decorator:** Use @classmethod after @field_validator
3. **Not using Field(...) for required fields:** Required fields use `Field(...)`

---

## TASK 04: Cover Letter Prompt

**File:** `src/backend/careervp/logic/prompts/cover_letter_prompt.py` (new)
**Purpose:** LLM prompt construction with anti-AI detection patterns
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 16

### Files to Create

```
src/backend/careervp/logic/prompts/cover_letter_prompt.py
tests/cover-letter/unit/test_cover_letter_prompt.py
```

### Key Implementation Details

1. **Define Anti-AI Guidelines:**
```python
ANTI_AI_GUIDELINES = """
CRITICAL WRITING GUIDELINES (Anti-AI Detection):
1. VARY sentence structure - mix short punchy sentences with longer ones
2. USE natural transitions - avoid "Furthermore", "Moreover", "Additionally"
3. AVOID buzzwords - no "synergy", "leverage", "innovative solutions"
4. INCLUDE specific details - numbers, dates, project names where possible
5. WRITE conversationally - use contractions occasionally ("I'm", "I've")
6. START sentences differently - don't begin multiple sentences with "I"
7. USE active voice predominantly
8. AVOID lists in cover letters - use flowing paragraphs
"""
```

2. **Define Tone Guidelines:**
```python
TONE_GUIDELINES = {
    "professional": """
TONE: Professional and confident
- Use formal language but remain approachable
- Emphasize expertise and proven track record
- Example phrases: "demonstrated expertise", "proven ability"
""",
    "enthusiastic": """
TONE: Enthusiastic and energetic
- Express genuine excitement about the opportunity
- Example phrases: "excited to", "passionate about"
""",
    "technical": """
TONE: Technical and precise
- Lead with technical accomplishments
- Example phrases: "architected", "implemented", "engineered"
""",
}
```

3. **Implement build_system_prompt:**
```python
def build_system_prompt(preferences: CoverLetterPreferences) -> str:
    """Build system prompt for cover letter generation."""
    tone_guide = TONE_GUIDELINES.get(preferences.tone, TONE_GUIDELINES["professional"])
    word_count = preferences.word_count_target

    return f"""You are an expert cover letter writer.

{ANTI_AI_GUIDELINES}

{tone_guide}

WORD COUNT: Target {word_count} words (acceptable range: {word_count - 50} to {word_count + 50})

FVS RULES (CRITICAL - DO NOT VIOLATE):
- Company name MUST match exactly as provided
- Job title MUST match exactly as provided
- Do NOT invent company details

OUTPUT FORMAT:
- Return ONLY the cover letter text
- No salutation (will be added separately)
- No signature (will be added separately)
"""
```

4. **Implement build_user_prompt:**
```python
def build_user_prompt(
    context: dict,
    company_name: str,
    job_title: str,
    preferences: CoverLetterPreferences,
) -> str:
    """Build user prompt with VPR context."""
    accomplishments = context.get("accomplishments", [])
    job_requirements = context.get("job_requirements", [])
    skills = context.get("skills", [])
    gap_responses = context.get("gap_responses", [])

    # Build accomplishments section (limit to top 5)
    accomplishments_text = ""
    if accomplishments:
        accomplishments_text = "KEY ACCOMPLISHMENTS:\n"
        for acc in accomplishments[:5]:
            accomplishments_text += f"- {acc.get('text', '')}\n"

    # Build requirements section
    requirements_text = ""
    if job_requirements:
        requirements_text = "JOB REQUIREMENTS:\n"
        for req in job_requirements[:5]:
            requirements_text += f"- {req}\n"

    return f"""Write a cover letter for:

COMPANY: {company_name}
POSITION: {job_title}

{accomplishments_text}
{requirements_text}

Target word count: {preferences.word_count_target} words
Company name must be exactly: {company_name}
Job title must be exactly: {job_title}
"""
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run ruff format careervp/logic/prompts/cover_letter_prompt.py
uv run ruff check --fix careervp/logic/prompts/cover_letter_prompt.py
uv run mypy careervp/logic/prompts/cover_letter_prompt.py --strict
uv run pytest tests/cover-letter/unit/test_cover_letter_prompt.py -v

# Expected: 16 tests PASSED
```

### Common Mistakes to Avoid

1. **Missing anti-AI guidelines:** All 8 guidelines must be in system prompt
2. **Not limiting accomplishments:** Limit to top 5 to keep prompt concise
3. **Hardcoding tone:** Use `TONE_GUIDELINES.get(tone, default)` for fallback

---

## TASK 03: Cover Letter Logic

**File:** `src/backend/careervp/logic/cover_letter_generator.py` (new)
**Purpose:** Core cover letter generation with quality scoring
**Complexity:** HIGH | **Duration:** 3 hours | **Tests:** 27

### Files to Create

```
src/backend/careervp/logic/cover_letter_generator.py
tests/cover-letter/unit/test_cover_letter_logic.py
```

### Key Implementation Details

1. **Define Constants:**
```python
# Quality score weights (MUST sum to 1.0)
PERSONALIZATION_WEIGHT = 0.40
RELEVANCE_WEIGHT = 0.35
TONE_WEIGHT = 0.25

# Quality thresholds
QUALITY_EXCELLENT = 0.80
QUALITY_GOOD = 0.70
QUALITY_RETRY_THRESHOLD = 0.70

# LLM configuration
DEFAULT_TIMEOUT_SECONDS = 300
MAX_RETRIES = 3
```

2. **Implement generate_cover_letter:**
```python
@tracer.capture_method
async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    user_id: str,
    llm_client: LLMClient,
    dal: DynamoDalHandler,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Result[TailoredCoverLetter]:
    """Generate personalized cover letter using LLM."""
    try:
        # Step 1: Retrieve master CV
        cv_result = await dal.get_cv_by_id(request.cv_id, user_id)
        if not cv_result.success:
            return Result.failure(
                error=f"CV not found: {request.cv_id}",
                code=ResultCode.CV_NOT_FOUND,
            )

        # Step 2: Retrieve VPR (required)
        vpr_result = await dal.get_vpr_artifact(request.cv_id, request.job_id)
        if not vpr_result.success:
            return Result.failure(
                error="VPR not found - generate VPR first",
                code=ResultCode.VPR_NOT_FOUND,
            )

        # Step 3: Build context
        context = build_personalization_context(
            cv=cv_result.data,
            vpr=vpr_result.data,
        )

        # Step 4: Build prompts
        preferences = request.preferences or CoverLetterPreferences()
        system_prompt = build_system_prompt(preferences)
        user_prompt = build_user_prompt(
            context=context,
            company_name=request.company_name,
            job_title=request.job_title,
            preferences=preferences,
        )

        # Step 5: Generate with Haiku (with timeout)
        llm_response = await asyncio.wait_for(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task_mode=TaskMode.TEMPLATE,
                model="claude-haiku-4-5",
            ),
            timeout=timeout,
        )

        # Step 6: Calculate quality score
        quality_scores = calculate_quality_score(
            content=llm_response.content,
            context=context,
            preferences=preferences,
        )
        overall_score = (
            PERSONALIZATION_WEIGHT * quality_scores["personalization"] +
            RELEVANCE_WEIGHT * quality_scores["relevance"] +
            TONE_WEIGHT * quality_scores["tone"]
        )

        # Step 7: Retry with Sonnet if quality too low
        if overall_score < QUALITY_RETRY_THRESHOLD:
            logger.warning("Quality below threshold, retrying with Sonnet")
            llm_response = await asyncio.wait_for(
                llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    task_mode=TaskMode.TEMPLATE,
                    model="claude-sonnet-4-5",
                ),
                timeout=timeout,
            )
            # Recalculate quality
            quality_scores = calculate_quality_score(...)

        # Step 8: Create TailoredCoverLetter
        cover_letter = TailoredCoverLetter(
            cover_letter_id=f"cl_{request.cv_id}_{request.job_id}_{int(datetime.now().timestamp())}",
            cv_id=request.cv_id,
            job_id=request.job_id,
            user_id=user_id,
            company_name=request.company_name,
            job_title=request.job_title,
            content=llm_response.content,
            word_count=len(llm_response.content.split()),
            personalization_score=quality_scores["personalization"],
            relevance_score=quality_scores["relevance"],
            tone_score=quality_scores["tone"],
            generated_at=datetime.now(),
        )

        return Result.success(
            data=cover_letter,
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS,
        )

    except asyncio.TimeoutError:
        return Result.failure(
            error=f"Cover letter generation timed out after {timeout}s",
            code=ResultCode.CV_LETTER_GENERATION_TIMEOUT,
        )
```

3. **Implement calculate_quality_score:**
```python
def calculate_quality_score(
    content: str,
    context: dict,
    preferences: CoverLetterPreferences,
) -> dict[str, float]:
    """Calculate quality scores for cover letter."""
    return {
        "personalization": _calculate_personalization_score(content, context),
        "relevance": _calculate_relevance_score(content, context),
        "tone": _calculate_tone_score(content, preferences),
    }

def _calculate_personalization_score(content: str, context: dict) -> float:
    """Score based on VPR accomplishments mentioned."""
    accomplishments = context.get("accomplishments", [])
    if not accomplishments:
        return 0.5

    mentioned = sum(
        1 for acc in accomplishments
        if any(kw in content.lower() for kw in acc.get("keywords", []))
    )
    return min(1.0, mentioned / max(len(accomplishments), 1) * 1.5)

def _calculate_relevance_score(content: str, context: dict) -> float:
    """Score based on job requirements addressed."""
    requirements = context.get("job_requirements", [])
    if not requirements:
        return 0.5

    addressed = sum(1 for req in requirements if req.lower() in content.lower())
    return min(1.0, addressed / max(len(requirements), 1))

def _calculate_tone_score(content: str, preferences: CoverLetterPreferences) -> float:
    """Score based on tone matching preferences."""
    tone_indicators = {
        "professional": ["experience", "expertise", "professional", "proven"],
        "enthusiastic": ["excited", "passionate", "eager", "thrilled"],
        "technical": ["implemented", "architected", "designed", "engineered"],
    }

    indicators = tone_indicators.get(preferences.tone, [])
    matches = sum(1 for ind in indicators if ind in content.lower())
    return min(1.0, matches / len(indicators) * 2) if indicators else 0.7
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run ruff format careervp/logic/cover_letter_generator.py
uv run ruff check --fix careervp/logic/cover_letter_generator.py
uv run mypy careervp/logic/cover_letter_generator.py --strict
uv run pytest tests/cover-letter/unit/test_cover_letter_logic.py -v

# Expected: 27 tests PASSED
```

### Common Mistakes to Avoid

1. **Missing VPR check:** Always return VPR_NOT_FOUND if VPR doesn't exist
2. **Wrong quality weights:** Verify 0.40 + 0.35 + 0.25 = 1.0
3. **Not handling timeout:** Wrap LLM call in asyncio.wait_for()
4. **Not retrying with Sonnet:** Check quality threshold and fallback

---

## TASK 05: FVS Integration

**File:** `src/backend/careervp/logic/fvs_cover_letter.py` (new)
**Purpose:** Validate cover letter against FVS baseline
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 24

### Files to Create

```
src/backend/careervp/logic/fvs_cover_letter.py
tests/cover-letter/unit/test_fvs_integration.py
```

### Key Implementation Details

1. **Define FVS Models:**
```python
@dataclass
class FVSViolation:
    field: str
    expected: str
    actual: str
    severity: str  # "critical" or "warning"
    message: str

@dataclass
class FVSValidationResult:
    is_valid: bool
    violations: list[FVSViolation]
    warnings: list[FVSViolation]

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == "critical" for v in self.violations)

@dataclass
class FVSBaseline:
    company_name: str
    job_title: str
    company_variations: list[str]
```

2. **Implement create_fvs_baseline:**
```python
def create_fvs_baseline(company_name: str, job_title: str) -> FVSBaseline:
    """Create FVS baseline from job details."""
    variations = generate_company_variations(company_name)
    return FVSBaseline(
        company_name=company_name,
        job_title=job_title,
        company_variations=variations,
    )

def generate_company_variations(company_name: str) -> list[str]:
    """Generate acceptable company name variations."""
    variations = [company_name]
    name = company_name.lower()

    # Remove common suffixes
    suffixes = [" inc.", " inc", " llc", " ltd", " corp", " corporation"]
    for suffix in suffixes:
        if name.endswith(suffix):
            variations.append(company_name[:-len(suffix)])
            break

    return variations
```

3. **Implement validate_cover_letter:**
```python
def validate_cover_letter(
    content: str,
    baseline: FVSBaseline,
    strict_mode: bool = False,
) -> FVSValidationResult:
    """Validate cover letter against FVS baseline."""
    violations = []
    warnings = []

    # Validate company name (CRITICAL if missing)
    company_result = _validate_company_name(content, baseline)
    if company_result:
        if company_result.severity == "critical":
            violations.append(company_result)
        else:
            warnings.append(company_result)

    # Validate job title (WARNING if missing)
    title_result = _validate_job_title(content, baseline)
    if title_result:
        if strict_mode:
            violations.append(title_result)
        else:
            warnings.append(title_result)

    return FVSValidationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
    )

def _validate_company_name(content: str, baseline: FVSBaseline) -> Optional[FVSViolation]:
    """Validate company name appears in content."""
    content_lower = content.lower()

    # Check exact match
    if baseline.company_name.lower() in content_lower:
        return None

    # Check variations
    for variation in baseline.company_variations:
        if variation.lower() in content_lower:
            return None

    # No match found - CRITICAL violation
    return FVSViolation(
        field="company_name",
        expected=baseline.company_name,
        actual="[not found]",
        severity="critical",
        message=f"Company name '{baseline.company_name}' not found",
    )
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run ruff format careervp/logic/fvs_cover_letter.py
uv run ruff check --fix careervp/logic/fvs_cover_letter.py
uv run mypy careervp/logic/fvs_cover_letter.py --strict
uv run pytest tests/cover-letter/unit/test_fvs_integration.py -v

# Expected: 24 tests PASSED
```

### Common Mistakes to Avoid

1. **Case sensitivity:** Always compare lowercase versions
2. **Not handling suffixes:** "TechCorp Inc." should match "TechCorp"
3. **Wrong severity:** Company = CRITICAL, Job title = WARNING

---

## TASK 07: DAL Extensions

**File:** `src/backend/careervp/dal/dynamo_dal_handler.py` (extend existing)
**Purpose:** Add methods for cover letter artifact storage
**Complexity:** Low | **Duration:** 1 hour | **Tests:** 14

### Files to Modify

```
src/backend/careervp/dal/dynamo_dal_handler.py  # Extend
tests/cover-letter/unit/test_cover_letter_dal_unit.py  # Create
```

### Key Implementation Details

1. **Add save_cover_letter_artifact method:**
```python
async def save_cover_letter_artifact(
    self,
    cover_letter: TailoredCoverLetter,
) -> Result[str]:
    """Save cover letter artifact to DynamoDB."""
    try:
        ttl = int(time.time()) + 7776000  # 90 days

        item = {
            "pk": cover_letter.user_id,
            "sk": f"ARTIFACT#COVER_LETTER#{cover_letter.cv_id}#{cover_letter.job_id}#v1",
            "artifact_type": "COVER_LETTER",
            "cv_id": cover_letter.cv_id,
            "job_id": cover_letter.job_id,
            "company_name": cover_letter.company_name,
            "job_title": cover_letter.job_title,
            "content": cover_letter.content,
            "word_count": cover_letter.word_count,
            "personalization_score": cover_letter.personalization_score,
            "relevance_score": cover_letter.relevance_score,
            "tone_score": cover_letter.tone_score,
            "generated_at": cover_letter.generated_at.isoformat(),
            "ttl": ttl,
        }

        self.table.put_item(Item=item)
        return Result.success(data=item["sk"])

    except Exception as e:
        logger.exception("Failed to save cover letter artifact")
        return Result.failure(
            error="Failed to persist cover letter",
            code=ResultCode.STORAGE_ERROR,
        )
```

2. **Add get_cover_letter_artifact method:**
```python
async def get_cover_letter_artifact(
    self,
    user_id: str,
    cv_id: str,
    job_id: str,
    version: int = 1,
) -> Result[dict]:
    """Retrieve cover letter artifact from DynamoDB."""
    try:
        response = self.table.get_item(
            Key={
                "pk": user_id,
                "sk": f"ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v{version}",
            }
        )
        item = response.get("Item")
        if not item:
            return Result.failure(
                error="Cover letter not found",
                code=ResultCode.NOT_FOUND,
            )
        return Result.success(data=item)
    except Exception as e:
        logger.exception("Failed to retrieve cover letter artifact")
        return Result.failure(
            error="Failed to retrieve cover letter",
            code=ResultCode.STORAGE_ERROR,
        )
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run ruff format careervp/dal/dynamo_dal_handler.py
uv run ruff check --fix careervp/dal/dynamo_dal_handler.py
uv run mypy careervp/dal/dynamo_dal_handler.py --strict
uv run pytest tests/cover-letter/unit/test_cover_letter_dal_unit.py -v

# Expected: 14 tests PASSED
```

### Common Mistakes to Avoid

1. **Wrong TTL calculation:** 90 days = 7776000 seconds
2. **Wrong SK format:** Must be `ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v{version}`
3. **Missing error handling:** Always catch exceptions and return Result.failure

---

## TASK 06: Cover Letter Handler

**File:** `src/backend/careervp/handlers/cover_letter_handler.py` (new)
**Purpose:** Lambda handler for cover letter generation API
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 19

### Files to Create

```
src/backend/careervp/handlers/cover_letter_handler.py
tests/cover-letter/unit/test_cover_letter_handler_unit.py
```

### Key Implementation Details

1. **Handler Structure (follow cv_upload_handler.py pattern):**
```python
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

RESULT_CODE_TO_HTTP_STATUS = {
    ResultCode.COVER_LETTER_GENERATED_SUCCESS: 200,
    ResultCode.CV_NOT_FOUND: 404,
    ResultCode.JOB_NOT_FOUND: 404,
    ResultCode.VPR_NOT_FOUND: 400,
    ResultCode.FVS_HALLUCINATION_DETECTED: 400,
    ResultCode.CV_LETTER_GENERATION_TIMEOUT: 504,
    ResultCode.RATE_LIMIT_EXCEEDED: 429,
    ResultCode.INVALID_REQUEST: 400,
    ResultCode.UNAUTHORIZED: 401,
    ResultCode.INTERNAL_ERROR: 500,
}

@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Handle cover letter generation request."""
    try:
        # Step 1: Extract user_id from JWT
        user_id = extract_user_id(event)
        if not user_id:
            return error_response(401, ResultCode.UNAUTHORIZED, "Auth required")

        logger.append_keys(user_id=user_id)

        # Step 2: Parse request
        body = json.loads(event.get("body", "{}"))
        request = GenerateCoverLetterRequest(**body)

        # Step 3: Generate cover letter
        result = asyncio.run(
            generate_cover_letter(request, user_id, llm_client, dal)
        )

        if not result.success:
            status = RESULT_CODE_TO_HTTP_STATUS.get(result.code, 500)
            return error_response(status, result.code, result.error)

        cover_letter = result.data

        # Step 4: Validate with FVS
        baseline = create_fvs_baseline(request.company_name, request.job_title)
        fvs_result = validate_cover_letter(cover_letter.content, baseline)

        if fvs_result.has_critical_violations:
            return error_response(
                400,
                ResultCode.FVS_HALLUCINATION_DETECTED,
                "Cover letter contains factual errors",
            )

        # Step 5: Save artifact
        await dal.save_cover_letter_artifact(cover_letter)

        # Step 6: Build response
        response = TailoredCoverLetterResponse(
            success=True,
            cover_letter=cover_letter,
            fvs_validation=fvs_result,
            quality_score=cover_letter.overall_quality_score,
            code=ResultCode.COVER_LETTER_GENERATED_SUCCESS.value,
            processing_time_ms=int(context.get_remaining_time_in_millis()),
            cost_estimate=0.005,
        )

        return success_response(200, response.model_dump(mode="json"))

    except ValidationError as e:
        return error_response(400, ResultCode.INVALID_REQUEST, str(e))
    except Exception as e:
        logger.exception("Unexpected error")
        return error_response(500, ResultCode.INTERNAL_ERROR, "Internal error")
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run ruff format careervp/handlers/cover_letter_handler.py
uv run ruff check --fix careervp/handlers/cover_letter_handler.py
uv run mypy careervp/handlers/cover_letter_handler.py --strict
uv run pytest tests/cover-letter/unit/test_cover_letter_handler_unit.py -v

# Expected: 19 tests PASSED
```

### Common Mistakes to Avoid

1. **Missing asyncio.run():** Handler is sync, logic is async - use asyncio.run()
2. **Not catching ValidationError:** Pydantic raises ValidationError for invalid input
3. **Missing Powertools decorators:** All three decorators required

---

## TASK 02: Infrastructure (CDK)

**File:** `infra/careervp/api_construct.py` (modify)
**Purpose:** Add Lambda and API Gateway route for cover letter
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 28

### Files to Modify

```
infra/careervp/api_construct.py     # Add Lambda + route
infra/careervp/constants.py         # Add constants
```

### Key Implementation Details

1. **Add Constants:**
```python
# In constants.py
COVER_LETTER_LAMBDA_MEMORY = 512  # MB
COVER_LETTER_LAMBDA_TIMEOUT = 300  # seconds
COVER_LETTER_RESERVED_CONCURRENCY = 10
```

2. **Add Lambda Function:**
```python
# In api_construct.py
cover_letter_lambda = aws_lambda.Function(
    self, "CoverLetterLambda",
    runtime=aws_lambda.Runtime.PYTHON_3_12,
    handler="careervp.handlers.cover_letter_handler.lambda_handler",
    code=aws_lambda.Code.from_asset(...),
    memory_size=COVER_LETTER_LAMBDA_MEMORY,
    timeout=Duration.seconds(COVER_LETTER_LAMBDA_TIMEOUT),
    reserved_concurrent_executions=COVER_LETTER_RESERVED_CONCURRENCY,
    environment={
        "TABLE_NAME": self.table.table_name,
        "BEDROCK_MODEL_ID": "claude-haiku-4-5-20251001",
    },
)

# Grant permissions
self.table.grant_read_write_data(cover_letter_lambda)
```

3. **Add API Gateway Route:**
```python
api.add_routes({
    "POST /api/cover-letter": cover_letter_lambda,
})
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

# Synthesize CDK
npx cdk synth

# Run infrastructure tests
cd ..
uv run pytest tests/cover-letter/infrastructure/test_cover_letter_stack.py -v

# Expected: 28 tests PASSED
```

### Common Mistakes to Avoid

1. **Wrong timeout:** Must be 300 seconds (5 minutes) for LLM calls
2. **Missing permissions:** Lambda needs DynamoDB read/write access
3. **Wrong handler path:** Must be `careervp.handlers.cover_letter_handler.lambda_handler`

---

## TASK 09: Integration Tests

**File:** `tests/cover-letter/integration/test_cover_letter_handler_integration.py`
**Purpose:** Test complete flow (Handler -> Logic -> DAL -> LLM)
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 22

### Key Test Categories

1. **Happy Path Tests:**
```python
async def test_cover_letter_generation_happy_path():
    """Test complete flow with valid inputs."""
    # Arrange: Mock LLM response with valid cover letter
    # Act: Call handler with valid request
    # Assert: 200 status, cover_letter present, quality_score > 0.70
```

2. **Error Path Tests:**
```python
async def test_cv_not_found_returns_404():
    """Test 404 when CV doesn't exist."""

async def test_vpr_not_found_returns_400():
    """Test 400 when VPR doesn't exist."""

async def test_fvs_violation_returns_400():
    """Test 400 when FVS validation fails."""

async def test_llm_timeout_returns_504():
    """Test 504 when LLM times out."""
```

3. **Quality Score Tests:**
```python
async def test_low_quality_triggers_sonnet_fallback():
    """Test that quality < 0.70 triggers Sonnet retry."""
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/cover-letter/integration/test_cover_letter_handler_integration.py -v

# Expected: 22 tests PASSED
```

---

## TASK 10: E2E Verification

**File:** `tests/cover-letter/e2e/test_cover_letter_flow.py`
**Purpose:** End-to-end tests against deployed infrastructure
**Complexity:** Medium | **Duration:** 2 hours | **Tests:** 20

### Key Test Categories

1. **HTTP Flow Tests:**
```python
def test_e2e_cover_letter_api():
    """Test against actual API Gateway + Lambda."""
    # Make real HTTP POST to /api/cover-letter
    # Verify response format matches spec
    # Verify download URL is valid
```

2. **Authentication Tests:**
```python
def test_e2e_missing_auth_returns_401():
    """Test 401 when JWT missing."""

def test_e2e_invalid_token_returns_401():
    """Test 401 when JWT invalid."""
```

3. **Storage Tests:**
```python
def test_e2e_cover_letter_stored_in_dynamodb():
    """Verify artifact is stored in DynamoDB."""
```

### Verification Command

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/cover-letter/e2e/test_cover_letter_flow.py -v

# Expected: 20 tests PASSED
```

---

## TASK 11: Deployment

**Purpose:** Deploy infrastructure and verify in production
**Complexity:** Low | **Duration:** 1 hour

### Deployment Steps

```bash
# 1. Synthesize CDK
cd /Users/yitzchak/Documents/dev/careervp/infra
npx cdk synth

# 2. Deploy to dev
npx cdk deploy CoverLetterStack --environment dev

# 3. Verify Lambda exists
aws lambda get-function --function-name cover-letter-handler

# 4. Test API endpoint
curl -X POST https://api.careervp.dev/api/cover-letter \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "cv_id": "cv_123",
    "job_id": "job_456",
    "company_name": "TechCorp",
    "job_title": "Senior Engineer"
  }'

# 5. Check CloudWatch logs
aws logs tail /aws/lambda/cover-letter-handler --follow
```

---

# PART 5: COMMON PITFALLS

## Pitfall 1: Forgetting FVS Validation on Company/Job Title

**Problem:** Returning cover letter without FVS validation allows hallucinated company names.

**Symptom:** Cover letter mentions wrong company or job title.

**Solution:**
```python
# ALWAYS validate before returning
baseline = create_fvs_baseline(request.company_name, request.job_title)
fvs_result = validate_cover_letter(cover_letter.content, baseline)

if fvs_result.has_critical_violations:
    return Result.failure(
        error="FVS validation failed",
        code=ResultCode.FVS_HALLUCINATION_DETECTED,
    )
```

**Test:** `test_fvs_rejects_wrong_company_name()` must PASS.

---

## Pitfall 2: Wrong Quality Score Formula

**Problem:** Weights don't sum to 1.0, producing invalid scores.

**Symptom:** Quality scores > 1.0 or negative.

**Solution:**
```python
# CORRECT weights (sum to 1.0)
PERSONALIZATION_WEIGHT = 0.40
RELEVANCE_WEIGHT = 0.35
TONE_WEIGHT = 0.25

# Verify: 0.40 + 0.35 + 0.25 = 1.00
overall = (
    PERSONALIZATION_WEIGHT * personalization +
    RELEVANCE_WEIGHT * relevance +
    TONE_WEIGHT * tone
)
```

**Test:** `test_quality_score_weights_sum_to_one()` must PASS.

---

## Pitfall 3: Missing Timeout Handling

**Problem:** LLM call hangs forever, Lambda times out ungracefully.

**Symptom:** 502 Gateway Timeout instead of 504 with proper error.

**Solution:**
```python
try:
    llm_response = await asyncio.wait_for(
        llm_client.generate(...),
        timeout=300.0,  # 5 minutes
    )
except asyncio.TimeoutError:
    return Result.failure(
        error="Cover letter generation timed out",
        code=ResultCode.CV_LETTER_GENERATION_TIMEOUT,
    )
```

**Test:** `test_llm_timeout_returns_504()` must PASS.

---

## Pitfall 4: Not Using Result[T] Pattern

**Problem:** Logic functions return raw values, breaking error propagation.

**Symptom:** Exceptions instead of graceful errors.

**Solution:**
```python
# WRONG
def generate_cover_letter(...) -> TailoredCoverLetter:
    if not cv:
        raise ValueError("CV not found")
    return cover_letter

# CORRECT
def generate_cover_letter(...) -> Result[TailoredCoverLetter]:
    if not cv:
        return Result.failure(
            error="CV not found",
            code=ResultCode.CV_NOT_FOUND,
        )
    return Result.success(data=cover_letter)
```

**Test:** Every logic function returns `Result[T]`.

---

## Pitfall 5: Hardcoding Model Names

**Problem:** Model names hardcoded, can't change without code deployment.

**Symptom:** Can't switch between Haiku/Sonnet without code change.

**Solution:**
```python
# Read from environment or config
model = os.environ.get("BEDROCK_MODEL_ID", "claude-haiku-4-5")

llm_response = await llm_client.generate(
    ...,
    model=model,
)
```

**Test:** `test_model_from_environment()` must PASS.

---

## Pitfall 6: Missing Powertools Decorators

**Problem:** No observability, hard to debug production issues.

**Symptom:** No CloudWatch metrics, no X-Ray traces.

**Solution:**
```python
# ALL THREE decorators required
@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    ...
```

**Test:** `test_handler_has_powertools_decorators()` must PASS.

---

## Pitfall 7: Wrong DynamoDB Key Format

**Problem:** Can't retrieve stored cover letters.

**Symptom:** "Cover letter not found" for existing letters.

**Solution:**
```python
# CORRECT key format
sk = f"ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v{version}"

# WRONG (missing ARTIFACT prefix)
sk = f"COVER_LETTER#{cv_id}#{job_id}#v{version}"
```

**Test:** `test_cover_letter_storage_and_retrieval()` must PASS.

---

## Pitfall 8: Missing TTL Calculation

**Problem:** Cover letters never expire, DynamoDB fills up.

**Symptom:** Increasing storage costs, stale data.

**Solution:**
```python
import time

# 90 days TTL
TTL_90_DAYS = 7776000  # 90 * 24 * 60 * 60
ttl = int(time.time()) + TTL_90_DAYS

item = {
    "pk": user_id,
    "sk": sk,
    "ttl": ttl,  # DynamoDB TTL field
}
```

**Test:** `test_cover_letter_has_90_day_ttl()` must PASS.

---

## Pitfall 9: Not Handling Rate Limits

**Problem:** LLM rate limits crash handler.

**Symptom:** 500 errors when Bedrock rate limited.

**Solution:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def call_llm_with_retry(...):
    try:
        return await llm_client.generate(...)
    except RateLimitError:
        raise  # Retry will handle
```

**Test:** `test_rate_limit_retry()` must PASS.

---

## Pitfall 10: Forgetting to Update Tests After Fixes

**Problem:** Tests pass but code is broken.

**Symptom:** Green tests, red production.

**Solution:**
```bash
# Run tests AFTER every fix
uv run pytest tests/cover-letter/ -v

# Run with coverage to find untested code
uv run pytest tests/cover-letter/ --cov=careervp --cov-report=term-missing
```

**Test:** Coverage >= 90% for all files.

---

# PART 6: VERIFICATION COMMANDS

## Per-Task Verification

### After Each Task

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# 1. Format code
uv run ruff format careervp/path/to/file.py

# 2. Lint code
uv run ruff check --fix careervp/path/to/file.py

# 3. Type check
uv run mypy careervp/path/to/file.py --strict

# 4. Run task tests
uv run pytest tests/cover-letter/unit/test_file.py -v

# 5. Check coverage
uv run pytest tests/cover-letter/unit/test_file.py --cov=careervp.path.to.module --cov-report=term-missing
```

### Task-Specific Commands

| Task | Test Command | Expected Tests |
|------|--------------|----------------|
| 01 | `pytest tests/cover-letter/unit/test_validation.py -v` | 19 PASSED |
| 02 | `pytest tests/cover-letter/infrastructure/test_cover_letter_stack.py -v` | 28 PASSED |
| 03 | `pytest tests/cover-letter/unit/test_cover_letter_logic.py -v` | 27 PASSED |
| 04 | `pytest tests/cover-letter/unit/test_cover_letter_prompt.py -v` | 16 PASSED |
| 05 | `pytest tests/cover-letter/unit/test_fvs_integration.py -v` | 24 PASSED |
| 06 | `pytest tests/cover-letter/unit/test_cover_letter_handler_unit.py -v` | 19 PASSED |
| 07 | `pytest tests/cover-letter/unit/test_cover_letter_dal_unit.py -v` | 14 PASSED |
| 08 | `pytest tests/cover-letter/unit/test_cover_letter_models.py -v` | 27 PASSED |
| 09 | `pytest tests/cover-letter/integration/test_cover_letter_handler_integration.py -v` | 22 PASSED |
| 10 | `pytest tests/cover-letter/e2e/test_cover_letter_flow.py -v` | 20 PASSED |

## Phase-Wide Verification

### Before Claiming Completion

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# 1. Run ALL cover letter tests
uv run pytest tests/cover-letter/ -v --tb=short
# Expected: 216 tests PASSED

# 2. Check coverage
uv run pytest tests/cover-letter/ --cov=careervp --cov-report=html
# Expected: >= 90% coverage

# 3. Format all code
uv run ruff format careervp/
# Expected: No changes

# 4. Lint all code
uv run ruff check --fix careervp/
# Expected: No errors

# 5. Type check all code
uv run mypy careervp --strict
# Expected: No errors

# 6. Synthesize CDK
cd ../infra
npx cdk synth
# Expected: No errors
```

### Infrastructure Verification

```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

# Synthesize CloudFormation
npx cdk synth

# Deploy to dev
npx cdk deploy CoverLetterStack --environment dev

# Verify Lambda
aws lambda get-function --function-name cover-letter-handler

# Test API endpoint
curl -X POST https://api.careervp.dev/api/cover-letter \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"cv_123","job_id":"job_456","company_name":"TechCorp","job_title":"Engineer"}'
```

---

# PART 7: REFERENCE IMPLEMENTATION EXAMPLES

## Handler Pattern (from cv_upload_handler.py)

```python
"""
Lambda handler pattern with AWS Powertools.
Follow this structure for cover_letter_handler.py.
"""

import json
from typing import Any

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Handle API request.

    Args:
        event: API Gateway event with body, headers, requestContext
        context: Lambda context with remaining time, function name

    Returns:
        API Gateway response with statusCode, body, headers
    """
    try:
        # Step 1: Extract authentication
        user_id = extract_user_id(event)
        if not user_id:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Unauthorized"}),
                "headers": {"Content-Type": "application/json"},
            }

        logger.append_keys(user_id=user_id)

        # Step 2: Parse request body
        body = json.loads(event.get("body", "{}"))
        request = RequestModel(**body)

        logger.info("Processing request", request_id=request.id)

        # Step 3: Call business logic
        result = process_request(request, user_id)

        if not result.success:
            status_code = get_http_status(result.code)
            return {
                "statusCode": status_code,
                "body": json.dumps({
                    "success": False,
                    "error": result.error,
                    "code": result.code.value,
                }),
                "headers": {"Content-Type": "application/json"},
            }

        # Step 4: Record metrics
        metrics.add_metric(
            name="RequestProcessed",
            unit=MetricUnit.Count,
            value=1,
        )

        # Step 5: Return success response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "data": result.data.model_dump(mode="json"),
                "code": result.code.value,
            }),
            "headers": {"Content-Type": "application/json"},
        }

    except ValidationError as e:
        logger.warning("Validation error", errors=e.errors())
        return {
            "statusCode": 400,
            "body": json.dumps({
                "success": False,
                "error": "Invalid request",
                "details": e.errors(),
            }),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        logger.exception("Unexpected error")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": "Internal server error",
            }),
            "headers": {"Content-Type": "application/json"},
        }


def extract_user_id(event: dict) -> str | None:
    """Extract user_id from Cognito JWT claims."""
    try:
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    except (KeyError, TypeError):
        return None


def get_http_status(code: ResultCode) -> int:
    """Map result code to HTTP status."""
    mapping = {
        ResultCode.SUCCESS: 200,
        ResultCode.NOT_FOUND: 404,
        ResultCode.INVALID_INPUT: 400,
        ResultCode.UNAUTHORIZED: 401,
        ResultCode.TIMEOUT: 504,
        ResultCode.INTERNAL_ERROR: 500,
    }
    return mapping.get(code, 500)
```

---

## Logic Pattern (from vpr_generator.py)

```python
"""
Business logic pattern with Result[T].
Follow this structure for cover_letter_generator.py.
"""

import asyncio
from typing import Optional
from datetime import datetime

from aws_lambda_powertools import Logger, Tracer

from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPRResponse
from careervp.llm.llm_client import LLMClient, TaskMode
from careervp.dal.dynamo_dal_handler import DynamoDalHandler

logger = Logger()
tracer = Tracer()


@tracer.capture_method
async def generate_vpr(
    cv_id: str,
    user_id: str,
    llm_client: LLMClient,
    dal: DynamoDalHandler,
    timeout: int = 300,
) -> Result[VPRResponse]:
    """Generate Value Proposition Report.

    This function demonstrates the Result[T] pattern used throughout
    CareerVP. All logic functions MUST return Result[T].

    Args:
        cv_id: ID of the CV to analyze
        user_id: Authenticated user ID
        llm_client: LLM client for generation
        dal: DAL handler for data access
        timeout: Max seconds for LLM call

    Returns:
        Result[VPRResponse] with success/error/code
    """
    try:
        # Step 1: Retrieve CV from DAL
        logger.info("Fetching CV", cv_id=cv_id)
        cv_result = await dal.get_cv_by_id(cv_id, user_id)

        if not cv_result.success:
            logger.warning("CV not found", cv_id=cv_id)
            return Result.failure(
                error=f"CV with id {cv_id} not found",
                code=ResultCode.CV_NOT_FOUND,
            )

        cv = cv_result.data

        # Step 2: Build prompts
        system_prompt = build_vpr_system_prompt()
        user_prompt = build_vpr_user_prompt(cv)

        # Step 3: Call LLM with timeout
        logger.info("Calling LLM for VPR generation")
        try:
            llm_response = await asyncio.wait_for(
                llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    task_mode=TaskMode.STRATEGIC,  # VPR uses Sonnet
                    model="claude-sonnet-4-5",
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error("LLM timeout", timeout=timeout)
            return Result.failure(
                error=f"VPR generation timed out after {timeout}s",
                code=ResultCode.VPR_GENERATION_TIMEOUT,
            )

        # Step 4: Parse response
        try:
            vpr = parse_vpr_response(llm_response.content)
        except ValueError as e:
            logger.error("Failed to parse VPR response", error=str(e))
            return Result.failure(
                error="Failed to parse LLM response",
                code=ResultCode.LLM_PARSE_ERROR,
            )

        # Step 5: Store artifact
        artifact_result = await dal.save_vpr_artifact(vpr, cv_id, user_id)
        if not artifact_result.success:
            logger.warning("Failed to save VPR artifact", error=artifact_result.error)
            # Don't fail - VPR was generated successfully

        logger.info("VPR generated successfully", cv_id=cv_id)

        return Result.success(
            data=vpr,
            code=ResultCode.VPR_GENERATED_SUCCESS,
        )

    except Exception as e:
        logger.exception("Unexpected error in VPR generation")
        return Result.failure(
            error=str(e),
            code=ResultCode.INTERNAL_ERROR,
        )
```

---

## DAL Pattern (from dynamo_dal_handler.py)

```python
"""
DAL pattern for DynamoDB operations.
Follow this structure for cover letter DAL extensions.
"""

import time
from typing import Any, Optional

import boto3
from aws_lambda_powertools import Logger

from careervp.models.result import Result, ResultCode

logger = Logger()


class DynamoDalHandler:
    """DynamoDB Data Access Layer.

    All DAL methods return Result[T] for consistent error handling.
    """

    def __init__(self, table_name: Optional[str] = None):
        """Initialize DAL with DynamoDB table.

        Args:
            table_name: DynamoDB table name (from environment if not provided)
        """
        import os
        self.table_name = table_name or os.environ["TABLE_NAME"]
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)

    async def get_cv_by_id(
        self,
        cv_id: str,
        user_id: str,
    ) -> Result[dict]:
        """Retrieve CV by ID.

        Args:
            cv_id: CV identifier
            user_id: Owner user ID

        Returns:
            Result[dict] with CV data or error
        """
        try:
            response = self.table.get_item(
                Key={
                    "pk": user_id,
                    "sk": f"CV#{cv_id}",
                }
            )

            item = response.get("Item")
            if not item:
                return Result.failure(
                    error=f"CV {cv_id} not found",
                    code=ResultCode.CV_NOT_FOUND,
                )

            return Result.success(data=item)

        except Exception as e:
            logger.exception("Failed to retrieve CV", cv_id=cv_id)
            return Result.failure(
                error="Failed to retrieve CV",
                code=ResultCode.STORAGE_ERROR,
            )

    async def save_artifact(
        self,
        artifact: dict[str, Any],
    ) -> Result[str]:
        """Save artifact to DynamoDB.

        Args:
            artifact: Artifact data with pk, sk, and content

        Returns:
            Result[str] with artifact ID or error
        """
        try:
            # Add TTL if not present
            if "ttl" not in artifact:
                artifact["ttl"] = int(time.time()) + 7776000  # 90 days

            self.table.put_item(Item=artifact)

            logger.info(
                "Artifact saved",
                artifact_type=artifact.get("artifact_type"),
                sk=artifact.get("sk"),
            )

            return Result.success(data=artifact.get("sk", ""))

        except Exception as e:
            logger.exception("Failed to save artifact")
            return Result.failure(
                error="Failed to persist artifact",
                code=ResultCode.STORAGE_ERROR,
            )

    async def get_artifact(
        self,
        user_id: str,
        artifact_type: str,
        cv_id: str,
        job_id: str,
        version: int = 1,
    ) -> Result[dict]:
        """Retrieve artifact by composite key.

        Args:
            user_id: Owner user ID
            artifact_type: Type of artifact (CV_TAILORED, COVER_LETTER, etc.)
            cv_id: Source CV ID
            job_id: Target job ID
            version: Artifact version

        Returns:
            Result[dict] with artifact data or error
        """
        try:
            sk = f"ARTIFACT#{artifact_type}#{cv_id}#{job_id}#v{version}"

            response = self.table.get_item(
                Key={
                    "pk": user_id,
                    "sk": sk,
                }
            )

            item = response.get("Item")
            if not item:
                return Result.failure(
                    error=f"Artifact not found: {sk}",
                    code=ResultCode.NOT_FOUND,
                )

            return Result.success(data=item)

        except Exception as e:
            logger.exception("Failed to retrieve artifact", sk=sk)
            return Result.failure(
                error="Failed to retrieve artifact",
                code=ResultCode.STORAGE_ERROR,
            )
```

---

## Test Pattern (from existing tests)

```python
"""
Test pattern for unit tests.
Follow this structure for all cover letter tests.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from careervp.models.result import Result, ResultCode
from careervp.models.cover_letter_models import (
    GenerateCoverLetterRequest,
    CoverLetterPreferences,
    TailoredCoverLetter,
)


class TestGenerateCoverLetter:
    """Tests for generate_cover_letter function."""

    @pytest.fixture
    def mock_dal(self):
        """Create mock DAL handler."""
        dal = Mock()
        dal.get_cv_by_id = AsyncMock()
        dal.get_vpr_artifact = AsyncMock()
        dal.save_cover_letter_artifact = AsyncMock()
        return dal

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client."""
        client = Mock()
        client.generate = AsyncMock()
        return client

    @pytest.fixture
    def sample_request(self):
        """Create sample cover letter request."""
        return GenerateCoverLetterRequest(
            cv_id="cv_123",
            job_id="job_456",
            company_name="TechCorp",
            job_title="Senior Engineer",
            preferences=CoverLetterPreferences(
                tone="professional",
                word_count_target=300,
            ),
        )

    @pytest.fixture
    def sample_cover_letter(self):
        """Create sample generated cover letter."""
        return TailoredCoverLetter(
            cover_letter_id="cl_123",
            cv_id="cv_123",
            job_id="job_456",
            user_id="user_789",
            company_name="TechCorp",
            job_title="Senior Engineer",
            content="I am excited to apply for the Senior Engineer position at TechCorp.",
            word_count=15,
            personalization_score=0.8,
            relevance_score=0.8,
            tone_score=0.8,
            generated_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_generate_cover_letter_success(
        self,
        mock_dal,
        mock_llm_client,
        sample_request,
    ):
        """Test successful cover letter generation."""
        # Arrange
        mock_dal.get_cv_by_id.return_value = Result.success(data=Mock())
        mock_dal.get_vpr_artifact.return_value = Result.success(data=Mock(
            accomplishments=[],
            job_requirements=[],
        ))
        mock_llm_client.generate.return_value = Mock(
            content="I am excited to apply for TechCorp..."
        )

        # Act
        from careervp.logic.cover_letter_generator import generate_cover_letter
        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
        )

        # Assert
        assert result.success is True
        assert result.code == ResultCode.COVER_LETTER_GENERATED_SUCCESS
        assert result.data.company_name == "TechCorp"
        assert result.data.job_title == "Senior Engineer"

    @pytest.mark.asyncio
    async def test_generate_cover_letter_cv_not_found(
        self,
        mock_dal,
        mock_llm_client,
        sample_request,
    ):
        """Test error when CV not found."""
        # Arrange
        mock_dal.get_cv_by_id.return_value = Result.failure(
            error="CV not found",
            code=ResultCode.CV_NOT_FOUND,
        )

        # Act
        from careervp.logic.cover_letter_generator import generate_cover_letter
        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
        )

        # Assert
        assert result.success is False
        assert result.code == ResultCode.CV_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_cover_letter_vpr_not_found(
        self,
        mock_dal,
        mock_llm_client,
        sample_request,
    ):
        """Test error when VPR not found."""
        # Arrange
        mock_dal.get_cv_by_id.return_value = Result.success(data=Mock())
        mock_dal.get_vpr_artifact.return_value = Result.failure(
            error="VPR not found",
            code=ResultCode.VPR_NOT_FOUND,
        )

        # Act
        from careervp.logic.cover_letter_generator import generate_cover_letter
        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
        )

        # Assert
        assert result.success is False
        assert result.code == ResultCode.VPR_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_cover_letter_timeout(
        self,
        mock_dal,
        mock_llm_client,
        sample_request,
    ):
        """Test timeout handling."""
        import asyncio

        # Arrange
        mock_dal.get_cv_by_id.return_value = Result.success(data=Mock())
        mock_dal.get_vpr_artifact.return_value = Result.success(data=Mock(
            accomplishments=[],
            job_requirements=[],
        ))
        mock_llm_client.generate.side_effect = asyncio.TimeoutError()

        # Act
        from careervp.logic.cover_letter_generator import generate_cover_letter
        result = await generate_cover_letter(
            request=sample_request,
            user_id="user_789",
            llm_client=mock_llm_client,
            dal=mock_dal,
            timeout=1,
        )

        # Assert
        assert result.success is False
        assert result.code == ResultCode.CV_LETTER_GENERATION_TIMEOUT


class TestCalculateQualityScore:
    """Tests for quality score calculation."""

    def test_quality_score_high_personalization(self):
        """Test high personalization score when accomplishments mentioned."""
        from careervp.logic.cover_letter_generator import calculate_quality_score

        content = "Led team of 10 engineers to deliver project on time."
        context = {
            "accomplishments": [
                {"text": "Led team", "keywords": ["led", "team", "engineers"]},
            ],
            "job_requirements": ["leadership"],
        }
        preferences = CoverLetterPreferences(tone="professional")

        scores = calculate_quality_score(content, context, preferences)

        assert scores["personalization"] > 0.7

    def test_quality_score_weights_sum_to_one(self):
        """Test that quality score weights sum to 1.0."""
        from careervp.logic.cover_letter_generator import (
            PERSONALIZATION_WEIGHT,
            RELEVANCE_WEIGHT,
            TONE_WEIGHT,
        )

        total = PERSONALIZATION_WEIGHT + RELEVANCE_WEIGHT + TONE_WEIGHT

        assert total == 1.0

    def test_quality_score_professional_tone(self):
        """Test tone score for professional tone."""
        from careervp.logic.cover_letter_generator import calculate_quality_score

        content = "With my proven expertise and professional experience..."
        context = {"accomplishments": [], "job_requirements": []}
        preferences = CoverLetterPreferences(tone="professional")

        scores = calculate_quality_score(content, context, preferences)

        assert scores["tone"] > 0.5
```

---

# COMPLETION CHECKLIST

## Per-Task Checklist

After completing EACH task:

- [ ] Implementation complete (all functions implemented)
- [ ] All tests PASS (run pytest)
- [ ] `uv run ruff format` passes (no changes)
- [ ] `uv run ruff check --fix` passes (no errors)
- [ ] `uv run mypy --strict` passes (no type errors)
- [ ] Code coverage >= 90%
- [ ] Docstrings complete (all public functions)
- [ ] Type hints complete (all parameters and returns)
- [ ] No TODOs or FIXMEs in code

## Phase-Wide Checklist

Before claiming Phase 10 COMPLETE:

- [ ] All 11 tasks completed
- [ ] All 216 tests PASS
- [ ] Code coverage >= 90% overall
- [ ] All code quality checks pass (ruff format, ruff check, mypy --strict)
- [ ] Infrastructure deployed to dev
- [ ] E2E tests pass against deployed environment
- [ ] Architect verification APPROVED
- [ ] No open bugs or issues

**DO NOT claim completion until ALL boxes are checked.**

---

**Document Version:** 1.0
**Last Updated:** 2026-02-06
**Total Lines:** ~1,850
**Phase:** 10 - Cover Letter Generation
