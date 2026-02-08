# Architecture Update Plan

**Date:** 2026-02-08
**Based on:** DEEP_ANALYSIS_RESULTS.md
**Status:** Ready for Implementation

---

## Executive Summary

The deep analysis revealed significant deviations between design documentation and implementation, particularly in CV Tailoring. This plan addresses:

1. **CV Tailoring Implementation Fix** - Align implementation with Handler → Logic → DAL pattern
2. **Cover Letter Documentation** - Update prompts, specs, tasks, tests
3. **Gap Analysis Documentation** - Update prompts, specs, tasks, tests
4. **Model Consolidation** - Unify UserCV and FVS models across all features

> **CORRECTION:** Deep analysis incorrectly reported "CV Tailoring tests missing" (Critical Issue #4).
> Tests exist at `tests/cv-tailoring/` (not `src/backend/tests/`):
> - `unit/` - 7 test files (handler, logic, models, prompt, validation, dal, fvs)
> - `integration/` - handler integration tests
> - `infrastructure/` - stack tests
> - `e2e/` - flow tests
> - `conftest.py` - fixtures
>
> **Revised Critical Issues: 3 (not 4)**

---

## Reference Architecture: VPR Pattern

All 4 features (VPR, CV Tailoring, Cover Letter, Gap Analysis) must follow this pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│ HANDLER LAYER (handlers/{feature}_handler.py)                   │
├─────────────────────────────────────────────────────────────────┤
│ Responsibilities:                                               │
│ ✓ Parse API Gateway event                                       │
│ ✓ Validate input (Pydantic models)                              │
│ ✓ Extract user_id from JWT claims                               │
│ ✓ Initialize dependencies (DAL, LLM, FVS)                       │
│ ✓ Delegate ALL business logic to Logic layer                    │
│ ✓ Format HTTP response from Result[T]                           │
│                                                                 │
│ ✗ NO direct DAL access (no get_item, put_item)                  │
│ ✗ NO business logic                                             │
│ ✗ NO LLM calls                                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ LOGIC LAYER (logic/{feature}_logic.py or {feature}_generator.py)│
├─────────────────────────────────────────────────────────────────┤
│ Responsibilities:                                               │
│ ✓ Receive request model + injected dependencies                 │
│ ✓ Fetch required data from DAL                                  │
│ ✓ Build prompts using prompt module                             │
│ ✓ Call LLM client                                               │
│ ✓ Parse LLM response                                            │
│ ✓ Validate with FVS                                             │
│ ✓ Store artifacts via DAL                                       │
│ ✓ Return Result[T]                                              │
│                                                                 │
│ Constructor: __init__(self, dal: DalHandler, llm_client, fvs)   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ DAL LAYER (dal/dynamo_dal_handler.py - SHARED)                  │
├─────────────────────────────────────────────────────────────────┤
│ Responsibilities:                                               │
│ ✓ get_cv(user_id) -> UserCV                                     │
│ ✓ save_cv(cv) -> None                                           │
│ ✓ get_vpr(application_id, version) -> VPR                       │
│ ✓ save_vpr(vpr) -> None                                         │
│ ✓ get_tailored_cv(user_id, cv_id, job_id) -> TailoredCV         │
│ ✓ save_tailored_cv(tailored_cv) -> None                         │
│ ✓ get_cover_letter(user_id, cv_id, job_id) -> CoverLetter       │
│ ✓ save_cover_letter(cover_letter) -> None                       │
│ ✓ get_gap_questions(cv_id, job_id) -> list[GapQuestion]         │
│ ✓ save_gap_questions(questions) -> None                         │
│ ✓ get_gap_responses(user_id) -> list[GapResponse]               │
│ ✓ save_gap_responses(responses) -> None                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 1: CV Tailoring Implementation Fix (P0)

### Current State (DEVIATES from design)

**Problem Location:** `src/backend/careervp/handlers/cv_tailoring_handler.py:160-192`

```python
# CURRENT (WRONG) - Handler directly accesses DAL
def _fetch_and_tailor_cv(request: TailorCVRequest) -> Result[Any]:
    dal = CVTable()           # ❌ Direct instantiation in handler
    llm_client = LLMClient()  # ❌ Direct instantiation in handler

    response = dal.get_item({'cv_id': request.cv_id})  # ❌ DAL access in handler
    # ... business logic in handler
```

**Design Spec:** `CV_TAILORING_DESIGN.md:164-184` specifies:
- Handler: NO DIRECT DAL ACCESS
- Logic: CVTailoringLogic class with dependency injection

### Target State (Matches VPR pattern)

```python
# TARGET (CORRECT) - Handler delegates to Logic

# Handler (cv_tailoring_handler.py)
def handler(event, context):
    request = parse_request(event)
    user_id = get_user_id(event)

    # Initialize dependencies
    dal = DynamoDalHandler(table_name=TABLE_NAME)
    llm_client = LLMClient()
    fvs_validator = FVSValidator()

    # Delegate ALL business logic
    logic = CVTailoringLogic(dal=dal, llm_client=llm_client, fvs=fvs_validator)
    result = logic.tailor_cv(request, user_id)

    return format_response(result)

# Logic (cv_tailoring_logic.py)
class CVTailoringLogic:
    def __init__(self, dal: DalHandler, llm_client: LLMClient, fvs: FVSValidator):
        self.dal = dal
        self.llm_client = llm_client
        self.fvs = fvs

    def tailor_cv(self, request: TailorCVRequest, user_id: str) -> Result[TailoredCVResponse]:
        # Fetch CV from DAL (logic layer responsibility)
        cv = self.dal.get_cv(user_id)
        if not cv:
            return Result(success=False, code=ResultCode.CV_NOT_FOUND)

        # Build prompt, call LLM, validate FVS, store artifact
        # ... all business logic here
```

### Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| CVT-1 | Create `CVTailoringLogic` class with DI constructor | `logic/cv_tailoring_logic.py` (new) | 2h |
| CVT-2 | Move CV fetch from handler to logic | `handlers/cv_tailoring_handler.py`, `logic/cv_tailoring_logic.py` | 1h |
| CVT-3 | Replace `CVTable` with `DynamoDalHandler` | `logic/cv_tailoring_logic.py` | 2h |
| CVT-4 | Add CV Tailoring methods to `DynamoDalHandler` | `dal/dynamo_dal_handler.py` | 2h |
| CVT-5 | Use unified `UserCV` from `models/cv.py` | Multiple files | 1h |
| CVT-6 | Add idempotency key support | `handlers/cv_tailoring_handler.py`, `logic/cv_tailoring_logic.py` | 2h |
| CVT-7 | Add Powertools decorators | `handlers/cv_tailoring_handler.py` | 1h |
| CVT-8 | Add retry logic for LLM calls | `logic/cv_tailoring_logic.py` | 1h |
| CVT-9 | Update unit tests | `tests/cv_tailoring/` | 4h |
| CVT-10 | Update integration tests | `tests/cv_tailoring/` | 4h |

**Total Effort:** 20h

---

## Part 2: Cover Letter Documentation Update (P1)

### Current State

| Component | Status | Location |
|-----------|--------|----------|
| Design Doc | ✅ Complete | `docs/architecture/COVER_LETTER_DESIGN.md` |
| Spec | ⚠️ Needs update | `docs/specs/cover-letter/COVER_LETTER_SPEC.md` |
| Prompts | ❌ Missing | N/A |
| Tasks | ❌ Missing | N/A |
| Tests | ❌ Missing | N/A |

### Files to Create/Update

#### 2.1 Prompts (`logic/prompts/cover_letter_prompt.py`)

```python
"""Cover Letter LLM prompts per COVER_LETTER_DESIGN.md:1301-1457"""

def build_system_prompt(tone: str, word_count_target: int) -> str:
    """Build system prompt for cover letter generation."""
    # From COVER_LETTER_DESIGN.md:1305-1374

def build_user_prompt(
    cv: UserCV,
    vpr: VPRResponse,
    company_name: str,
    job_title: str,
    job_description: str,
    gap_responses: list[GapResponse] | None = None,
    emphasis_areas: list[str] | None = None,
) -> str:
    """Build user prompt for cover letter generation."""
    # From COVER_LETTER_DESIGN.md:1378-1457
```

#### 2.2 Spec Update (`docs/specs/cover-letter/COVER_LETTER_SPEC.md`)

Add sections:
- Handler → Logic → DAL implementation details
- DAL method signatures
- FVS validation rules
- Error codes and HTTP mappings
- Idempotency key format

#### 2.3 Tasks (`docs/tasks/cover-letter/COVER_LETTER_TASKS.md`)

| ID | Task | Priority | Depends On |
|----|------|----------|------------|
| CL-1 | Create `CoverLetterRequest` model | P0 | - |
| CL-2 | Create `CoverLetterResponse` model | P0 | - |
| CL-3 | Create `cover_letter_prompt.py` | P0 | - |
| CL-4 | Create `CoverLetterLogic` class | P0 | CL-1,2,3 |
| CL-5 | Add DAL methods for cover letters | P0 | - |
| CL-6 | Create `cover_letter_handler.py` | P0 | CL-4,5 |
| CL-7 | Add FVS validation for cover letters | P1 | CL-4 |
| CL-8 | Add quality scoring | P1 | CL-4 |
| CL-9 | Add Sonnet fallback | P2 | CL-4 |
| CL-10 | Create unit tests | P0 | CL-4,6 |
| CL-11 | Create integration tests | P1 | CL-10 |
| CL-12 | Create infrastructure stack | P0 | - |

#### 2.4 Tests (`tests/cover_letter/`)

```
tests/cover_letter/
├── unit/
│   ├── test_cover_letter_logic.py      # 27 tests
│   ├── test_cover_letter_prompt.py     # 16 tests
│   ├── test_cover_letter_models.py     # 27 tests
│   └── test_quality_scoring.py         # 27 tests
├── integration/
│   ├── test_cover_letter_handler.py    # 19 tests
│   └── test_cover_letter_dal.py        # 12 tests
├── infrastructure/
│   └── test_cover_letter_stack.py      # 28 tests
├── e2e/
│   └── test_cover_letter_flow.py       # 20 tests
└── conftest.py                         # 20+ fixtures
```

### Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| CLD-1 | Create `cover_letter_prompt.py` | `logic/prompts/cover_letter_prompt.py` | 3h |
| CLD-2 | Update `COVER_LETTER_SPEC.md` | `docs/specs/cover-letter/COVER_LETTER_SPEC.md` | 2h |
| CLD-3 | Create `COVER_LETTER_TASKS.md` | `docs/tasks/cover-letter/COVER_LETTER_TASKS.md` | 1h |
| CLD-4 | Create test file structure | `tests/cover_letter/` | 1h |
| CLD-5 | Create `conftest.py` with fixtures | `tests/cover_letter/conftest.py` | 2h |

**Total Effort:** 9h

---

## Part 3: Gap Analysis Documentation Update (P1)

### Current State

| Component | Status | Location |
|-----------|--------|----------|
| Design Doc | ✅ Complete | `docs/architecture/GAP_ANALYSIS_DESIGN.md` |
| Spec | ⚠️ Needs update | `docs/specs/gap-analysis/GAP_SPEC.md` |
| Prompts | ❌ Missing | N/A |
| Tasks | ❌ Missing | N/A |
| Tests | ❌ Missing | N/A |

### Files to Create/Update

#### 3.1 Prompts (`logic/prompts/gap_analysis_prompt.py`)

```python
"""Gap Analysis LLM prompts per GAP_ANALYSIS_DESIGN.md:371-467"""

def build_system_prompt() -> str:
    """Build system prompt for gap analysis."""
    # From GAP_ANALYSIS_DESIGN.md:381-423

def build_user_prompt(user_cv: UserCV, job_posting: JobPosting) -> str:
    """Build user prompt for gap analysis."""
    # From GAP_ANALYSIS_DESIGN.md:427-467
```

#### 3.2 Spec Update (`docs/specs/gap-analysis/GAP_SPEC.md`)

Add sections:
- Handler → Logic → DAL implementation details
- DAL method signatures
- FVS skill verification rules
- Error codes and HTTP mappings
- Gap scoring algorithm details

#### 3.3 Tasks (`docs/tasks/gap-analysis/GAP_ANALYSIS_TASKS.md`)

| ID | Task | Priority | Depends On |
|----|------|----------|------------|
| GA-1 | Create `GapAnalysisRequest` model | P0 | - |
| GA-2 | Create `GapQuestion` model | P0 | - |
| GA-3 | Create `gap_analysis_prompt.py` | P0 | - |
| GA-4 | Create `GapAnalysisLogic` class | P0 | GA-1,2,3 |
| GA-5 | Create `GapAnalysisFVSValidator` | P0 | GA-4 |
| GA-6 | Add DAL methods for gap analysis | P0 | - |
| GA-7 | Create `gap_analysis_handler.py` | P0 | GA-4,5,6 |
| GA-8 | Create gap responses endpoints | P1 | GA-7 |
| GA-9 | Create unit tests | P0 | GA-4,7 |
| GA-10 | Create integration tests | P1 | GA-9 |
| GA-11 | Create infrastructure stack | P0 | - |

#### 3.4 Tests (`tests/gap_analysis/`)

```
tests/gap_analysis/
├── unit/
│   ├── test_gap_analysis_logic.py      # 24 tests
│   ├── test_gap_analysis_prompt.py     # 12 tests
│   ├── test_gap_scoring.py             # 16 tests
│   └── test_gap_fvs_validator.py       # 18 tests
├── integration/
│   ├── test_gap_analysis_handler.py    # 15 tests
│   └── test_gap_analysis_dal.py        # 10 tests
├── infrastructure/
│   └── test_gap_analysis_stack.py      # 20 tests
├── e2e/
│   └── test_gap_analysis_flow.py       # 15 tests
└── conftest.py                         # 15+ fixtures
```

### Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| GAD-1 | Create `gap_analysis_prompt.py` | `logic/prompts/gap_analysis_prompt.py` | 2h |
| GAD-2 | Update `GAP_SPEC.md` | `docs/specs/gap-analysis/GAP_SPEC.md` | 2h |
| GAD-3 | Create `GAP_ANALYSIS_TASKS.md` | `docs/tasks/gap-analysis/GAP_ANALYSIS_TASKS.md` | 1h |
| GAD-4 | Create test file structure | `tests/gap_analysis/` | 1h |
| GAD-5 | Create `conftest.py` with fixtures | `tests/gap_analysis/conftest.py` | 2h |

**Total Effort:** 8h

---

## Part 4: Model Consolidation (P0)

### Current State (Duplicates)

| Model | File 1 | File 2 | Used By |
|-------|--------|--------|---------|
| `UserCV` | `models/cv.py` | `models/cv_models.py` | VPR uses cv.py, CV Tailoring uses cv_models.py |
| `FVSBaseline` | `models/fvs.py` | `models/fvs_models.py` | Mixed usage |

### Target State (Unified)

| Model | Canonical Location | Action |
|-------|-------------------|--------|
| `UserCV` | `models/cv.py` | Keep, migrate references |
| `cv_models.py` | - | DELETE after migration |
| `FVSBaseline` | `models/fvs.py` | Keep, migrate references |
| `fvs_models.py` | - | DELETE after migration |

### Migration Steps

#### 4.1 UserCV Consolidation

```python
# Keep: models/cv.py (VPR uses this)
# Delete: models/cv_models.py (CV Tailoring uses this)

# Migration:
# 1. Compare both UserCV definitions
# 2. Merge any unique fields from cv_models.py into cv.py
# 3. Update all imports in CV Tailoring to use models.cv
# 4. Delete cv_models.py
```

#### 4.2 FVS Model Consolidation

```python
# Keep: models/fvs.py
# Delete: models/fvs_models.py

# Migration:
# 1. Compare both FVS model definitions
# 2. Merge any unique fields/classes
# 3. Update all imports
# 4. Delete fvs_models.py
```

### Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| MDL-1 | Compare UserCV models, identify differences | `models/cv.py`, `models/cv_models.py` | 1h |
| MDL-2 | Merge unique fields into `models/cv.py` | `models/cv.py` | 2h |
| MDL-3 | Update CV Tailoring imports to use `models.cv` | Multiple files | 2h |
| MDL-4 | Delete `models/cv_models.py` | - | 0.5h |
| MDL-5 | Compare FVS models, identify differences | `models/fvs.py`, `models/fvs_models.py` | 1h |
| MDL-6 | Merge unique fields into `models/fvs.py` | `models/fvs.py` | 1h |
| MDL-7 | Update all FVS imports | Multiple files | 1h |
| MDL-8 | Delete `models/fvs_models.py` | - | 0.5h |
| MDL-9 | Run all tests to verify no regressions | - | 1h |

**Total Effort:** 10h

---

## Part 5: DAL Enhancement (P0)

### Current State

`DynamoDalHandler` has methods for VPR only. Need to add methods for all features.

### Target State

```python
class DynamoDalHandler(DalHandler):
    # Existing (VPR)
    def save_cv(self, user_cv: UserCV) -> None: ...
    def get_cv(self, user_id: str) -> UserCV | None: ...
    def save_vpr(self, vpr: VPR) -> Result[None]: ...
    def get_vpr(self, application_id: str, version: int | None) -> Result[VPR | None]: ...
    def get_latest_vpr(self, application_id: str) -> Result[VPR | None]: ...
    def list_vprs(self, user_id: str) -> Result[list[VPR]]: ...

    # NEW: CV Tailoring
    def save_tailored_cv(self, tailored_cv: TailoredCV) -> Result[None]: ...
    def get_tailored_cv(self, user_id: str, cv_id: str, job_id: str) -> Result[TailoredCV | None]: ...
    def list_tailored_cvs(self, user_id: str) -> Result[list[TailoredCV]]: ...

    # NEW: Cover Letter
    def save_cover_letter(self, cover_letter: CoverLetter) -> Result[None]: ...
    def get_cover_letter(self, user_id: str, cv_id: str, job_id: str) -> Result[CoverLetter | None]: ...
    def list_cover_letters(self, user_id: str) -> Result[list[CoverLetter]]: ...

    # NEW: Gap Analysis
    def save_gap_questions(self, cv_id: str, job_id: str, questions: list[GapQuestion]) -> Result[None]: ...
    def get_gap_questions(self, cv_id: str, job_id: str) -> Result[list[GapQuestion] | None]: ...
    def save_gap_responses(self, user_id: str, responses: list[GapResponse]) -> Result[None]: ...
    def get_gap_responses(self, user_id: str) -> Result[list[GapResponse]]: ...
```

### Artifact Storage Schema

All artifacts follow the same pattern:

```
PK: user_id
SK: ARTIFACT#{artifact_type}#{cv_id}#{job_id}#v{version}
TTL: 90 days
```

| Artifact Type | SK Pattern | Example |
|---------------|------------|---------|
| VPR | `ARTIFACT#VPR#v{version}` | `ARTIFACT#VPR#v1` |
| CV_TAILORED | `ARTIFACT#CV_TAILORED#{cv_id}#{job_id}#v{version}` | `ARTIFACT#CV_TAILORED#cv_abc#job_xyz#v1` |
| COVER_LETTER | `ARTIFACT#COVER_LETTER#{cv_id}#{job_id}#v{version}` | `ARTIFACT#COVER_LETTER#cv_abc#job_xyz#v1` |
| GAP_ANALYSIS | `ARTIFACT#GAP_ANALYSIS#{cv_id}#{job_id}` | `ARTIFACT#GAP_ANALYSIS#cv_abc#job_xyz` |

### Tasks

| ID | Task | File(s) | Effort |
|----|------|---------|--------|
| DAL-1 | Add CV Tailoring methods | `dal/dynamo_dal_handler.py` | 3h |
| DAL-2 | Add Cover Letter methods | `dal/dynamo_dal_handler.py` | 3h |
| DAL-3 | Add Gap Analysis methods | `dal/dynamo_dal_handler.py` | 3h |
| DAL-4 | Add Gap Response methods | `dal/dynamo_dal_handler.py` | 2h |
| DAL-5 | Create DAL unit tests | `tests/dal/test_dynamo_dal_handler.py` | 4h |
| DAL-6 | Deprecate and remove `CVTable` | `dal/cv_dal.py` | 1h |
| DAL-7 | Deprecate and remove `cv_tailoring_dal.py` | `dal/cv_tailoring_dal.py` | 1h |

**Total Effort:** 17h

---

## Implementation Order

Based on dependencies and priority:

### Phase 1: Foundation (Week 1)

| Priority | Task Group | Effort | Depends On |
|----------|------------|--------|------------|
| P0 | Model Consolidation (MDL-1 to MDL-9) | 10h | - |
| P0 | DAL Enhancement (DAL-1 to DAL-7) | 17h | MDL-* |

### Phase 2: CV Tailoring Fix (Week 2)

| Priority | Task Group | Effort | Depends On |
|----------|------------|--------|------------|
| P0 | CV Tailoring Fix (CVT-1 to CVT-10) | 20h | DAL-* |

### Phase 3: Documentation (Week 3)

| Priority | Task Group | Effort | Depends On |
|----------|------------|--------|------------|
| P1 | Cover Letter Docs (CLD-1 to CLD-5) | 9h | - |
| P1 | Gap Analysis Docs (GAD-1 to GAD-5) | 8h | - |

---

## Total Effort Summary

| Component | Hours |
|-----------|-------|
| Model Consolidation | 10h |
| DAL Enhancement | 17h |
| CV Tailoring Fix | 20h |
| Cover Letter Docs | 9h |
| Gap Analysis Docs | 8h |
| **TOTAL** | **64h** |

---

## Verification Checklist

Before marking complete, verify:

- [ ] All 4 features follow Handler → Logic → DAL pattern
- [ ] Single `UserCV` model in `models/cv.py`
- [ ] Single FVS model set in `models/fvs.py`
- [ ] All DAL access goes through `DynamoDalHandler`
- [ ] CV Tailoring handler has NO direct DAL access
- [ ] CV Tailoring has idempotency support
- [ ] CV Tailoring has Powertools observability
- [ ] Cover Letter prompts defined
- [ ] Gap Analysis prompts defined
- [ ] All unit tests pass
- [ ] All integration tests pass

---

## Sign-Off

| Reviewer | Status | Date |
|----------|--------|------|
| Architect | PENDING | - |
| Tech Lead | PENDING | - |

---

**Document Version:** 1.0
**Created:** 2026-02-08
**Last Updated:** 2026-02-08
