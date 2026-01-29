# Task 9.1: CV Tailoring - Pydantic Models

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 1 (CV Models), Task 8 (Company Research Models)

## Overview

Implement Pydantic models for the CV tailoring feature, including request/response schemas, tailored CV structure, and supporting types. All models must follow the FVS tier classification system (IMMUTABLE, VERIFIABLE, FLEXIBLE) and support the optional `gap_analysis` parameter for Phase 11 extensibility.

## Todo

### Models Implementation

- [ ] Create `src/backend/careervp/models/tailor.py`
- [ ] Implement `StylePreferences` model for output customization
- [ ] Implement `TailorCVRequest` model for API input validation
- [ ] Implement `TailoredSkill` model with relevance scoring
- [ ] Implement `TailoredWorkExperience` model with IMMUTABLE/FLEXIBLE separation
- [ ] Implement `TailoredCV` model as main output structure
- [ ] Implement `TailoringMetadata` model for tracking modifications
- [ ] Implement `TailoredCVData` model combining CV and metadata
- [ ] Implement `TailorCVResponse` model for API response
- [ ] Add `ResultCode.CV_TAILORED` and `ResultCode.CV_TAILORING_FAILED` to `result.py`

### Validation

- [ ] Run `uv run ruff format src/backend/careervp/models/tailor.py`
- [ ] Run `uv run ruff check --fix src/backend/careervp/models/`
- [ ] Run `uv run mypy src/backend/careervp/models/ --strict`

### Commit

- [ ] Commit with message: `feat(models): add CV tailoring Pydantic models`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/models/tailor.py` | All CV tailoring models |
| `src/backend/careervp/models/result.py` | Add new ResultCode constants |
| `src/backend/careervp/models/__init__.py` | Export new models |

### Key Implementation Details

```python
"""
Pydantic models for CV Tailoring.
Per docs/specs/04-cv-tailoring.md.

FVS Tier Classification:
- IMMUTABLE: Cannot be altered (dates, titles, company names, degrees)
- VERIFIABLE: Must exist in source CV (skills, certifications)
- FLEXIBLE: Can be creatively reframed (summaries, bullet descriptions)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class StylePreferences(BaseModel):
    """Optional styling preferences for tailored CV output."""

    tone: Annotated[
        Literal['professional', 'conversational', 'technical'],
        Field(default='professional', description='Writing tone for tailored content'),
    ]
    formality_level: Annotated[
        Literal['high', 'medium', 'low'],
        Field(default='high', description='Formality level of language'),
    ]
    include_summary: Annotated[
        bool,
        Field(default=True, description='Whether to include executive summary'),
    ]


class TailorCVRequest(BaseModel):
    """
    Request payload for CV tailoring endpoint.
    Per docs/specs/04-cv-tailoring.md API Schema.
    """

    user_id: Annotated[str, Field(description='User identifier')]
    application_id: Annotated[str, Field(description='Job application identifier')]
    job_id: Annotated[str, Field(description='Target job posting identifier')]
    cv_version: Annotated[
        int,
        Field(default=1, ge=1, description='CV version to tailor'),
    ]
    include_gap_analysis: Annotated[
        bool,
        Field(default=False, description='Include gap analysis in tailoring context (Phase 11)'),
    ]
    output_format: Annotated[
        Literal['json', 'markdown'],
        Field(default='json', description='Output format for tailored CV'),
    ]
    style_preferences: Annotated[
        StylePreferences | None,
        Field(default=None, description='Optional styling preferences'),
    ]


class TailoredSkill(BaseModel):
    """
    Skill entry with job relevance scoring.
    Per docs/specs/04-cv-tailoring.md: VERIFIABLE - must exist in source CV.
    """

    # FVS_COMMENT: VERIFIABLE - skill name must exist in source CV
    skill_name: Annotated[str, Field(description='VERIFIABLE - Skill from source CV')]
    proficiency_level: Annotated[
        str | None,
        Field(default=None, description='VERIFIABLE - Proficiency if stated in source'),
    ]
    relevance_score: Annotated[
        float,
        Field(ge=0.0, le=1.0, description='Relevance to target job (0.0-1.0)'),
    ]
    matched_requirements: Annotated[
        list[str],
        Field(default_factory=list, description='Job requirements this skill addresses'),
    ]


class TailoredWorkExperience(BaseModel):
    """
    Work experience entry with tailored descriptions.
    Per docs/specs/04-cv-tailoring.md: Mixed IMMUTABLE and FLEXIBLE fields.
    """

    # FVS_COMMENT: IMMUTABLE - these fields cannot be altered
    company_name: Annotated[str, Field(description='IMMUTABLE - Company name from source')]
    job_title: Annotated[str, Field(description='IMMUTABLE - Job title from source')]
    start_date: Annotated[str, Field(description='IMMUTABLE - Start date from source')]
    end_date: Annotated[str | None, Field(default=None, description='IMMUTABLE - End date from source')]
    location: Annotated[str | None, Field(default=None, description='IMMUTABLE - Location from source')]

    # FVS_COMMENT: FLEXIBLE - these fields can be creatively reframed
    description_bullets: Annotated[
        list[str],
        Field(description='FLEXIBLE - Reframed achievement bullets'),
    ]
    keyword_alignments: Annotated[
        list[str],
        Field(default_factory=list, description='Keywords from job description matched'),
    ]

    # For FVS validation comparison
    original_bullets: Annotated[
        list[str],
        Field(description='Original bullets for FVS comparison'),
    ]


class TailoredCV(BaseModel):
    """
    Tailored CV output optimized for specific job application.
    Per docs/specs/04-cv-tailoring.md.
    """

    # Import ContactInfo, Education, Certification from cv.py
    # FVS_COMMENT: IMMUTABLE - contact info copied directly
    contact_info: Annotated[dict[str, str | None], Field(description='IMMUTABLE - Contact details from source CV')]

    # FVS_COMMENT: FLEXIBLE - executive summary allows creative liberty
    executive_summary: Annotated[
        str,
        Field(description='FLEXIBLE - Job-targeted professional summary'),
    ]

    # Mixed IMMUTABLE (dates, titles) and FLEXIBLE (bullets)
    work_experience: Annotated[
        list[TailoredWorkExperience],
        Field(description='MIXED - Reframed work experience'),
    ]

    # FVS_COMMENT: VERIFIABLE - skills must exist in source CV
    skills: Annotated[
        list[TailoredSkill],
        Field(description='VERIFIABLE - Skills with relevance scores'),
    ]

    # FVS_COMMENT: IMMUTABLE - education copied from source
    education: Annotated[
        list[dict[str, str | None]],
        Field(description='IMMUTABLE - Education from source'),
    ]

    # FVS_COMMENT: IMMUTABLE - certifications copied from source
    certifications: Annotated[
        list[dict[str, str | None]],
        Field(default_factory=list, description='IMMUTABLE - Certifications from source'),
    ]

    # Metadata for tracking
    source_cv_version: Annotated[int, Field(description='Version of source CV used')]
    target_job_id: Annotated[str, Field(description='Job posting this CV targets')]
    tailoring_version: Annotated[int, Field(default=1, description='Iteration of tailoring')]


class TailoringMetadata(BaseModel):
    """Metadata about the tailoring process."""

    application_id: Annotated[str, Field(description='Application identifier')]
    version: Annotated[int, Field(description='Tailoring version')]
    created_at: Annotated[datetime, Field(description='Timestamp of creation')]
    keyword_matches: Annotated[int, Field(description='Number of keywords matched')]
    sections_modified: Annotated[
        list[str],
        Field(description='List of sections that were modified'),
    ]
    fvs_validation_passed: Annotated[bool, Field(description='Whether FVS validation passed')]


class TokenUsage(BaseModel):
    """Token usage statistics from LLM call."""

    input_tokens: Annotated[int, Field(description='Input tokens consumed')]
    output_tokens: Annotated[int, Field(description='Output tokens generated')]
    model: Annotated[str, Field(description='Model identifier used')]


class TailoredCVData(BaseModel):
    """Combined tailored CV with metadata for API response."""

    tailored_cv: Annotated[TailoredCV, Field(description='The tailored CV')]
    metadata: Annotated[TailoringMetadata, Field(description='Tailoring metadata')]
    token_usage: Annotated[TokenUsage, Field(description='LLM token usage')]


class TailorCVResponse(BaseModel):
    """
    Response payload from CV tailoring endpoint.
    Per docs/specs/04-cv-tailoring.md API Schema.
    """

    success: Annotated[bool, Field(description='Whether tailoring succeeded')]
    data: Annotated[
        TailoredCVData | None,
        Field(default=None, description='Tailored CV and metadata on success'),
    ]
    error: Annotated[str | None, Field(default=None, description='Error message on failure')]
    code: Annotated[str, Field(description='Machine-readable result code')]
    details: Annotated[
        dict[str, str] | None,
        Field(default=None, description='Additional error details'),
    ]
```

### ResultCode Additions

Add to `src/backend/careervp/models/result.py`:

```python
# CV Tailoring codes
CV_TAILORED = 'CV_TAILORED'
CV_TAILORING_FAILED = 'CV_TAILORING_FAILED'
CV_NOT_FOUND = 'CV_NOT_FOUND'
JOB_NOT_FOUND = 'JOB_NOT_FOUND'
COMPANY_RESEARCH_NOT_FOUND = 'COMPANY_RESEARCH_NOT_FOUND'
```

### Model Exports

Update `src/backend/careervp/models/__init__.py`:

```python
from careervp.models.tailor import (
    StylePreferences,
    TailorCVRequest,
    TailorCVResponse,
    TailoredCV,
    TailoredCVData,
    TailoredSkill,
    TailoredWorkExperience,
    TailoringMetadata,
    TokenUsage,
)

__all__ = [
    # ... existing exports ...
    'StylePreferences',
    'TailorCVRequest',
    'TailorCVResponse',
    'TailoredCV',
    'TailoredCVData',
    'TailoredSkill',
    'TailoredWorkExperience',
    'TailoringMetadata',
    'TokenUsage',
]
```

### FVS Tier Classification Rules

| Tier | Fields | Allowed Operations |
| ---- | ------ | ------------------ |
| IMMUTABLE | dates, titles, company names, degrees, certifications | Copy only |
| VERIFIABLE | skills, technologies, tools | Copy, reorder, highlight |
| FLEXIBLE | summaries, bullet descriptions | Reframe, rephrase, optimize |

### Zero-Hallucination Checklist

- [ ] All IMMUTABLE fields have `description='IMMUTABLE - ...'`
- [ ] All VERIFIABLE fields have `description='VERIFIABLE - ...'`
- [ ] All FLEXIBLE fields have `description='FLEXIBLE - ...'`
- [ ] `TailoredWorkExperience` includes `original_bullets` for FVS comparison
- [ ] No default values for IMMUTABLE fields (must come from source)
- [ ] `include_gap_analysis` parameter exists for Phase 11 extensibility

### Acceptance Criteria

- [ ] All models pass `mypy --strict` validation
- [ ] Models follow existing patterns in `cv.py` and `vpr.py`
- [ ] FVS tier classifications documented in Field descriptions
- [ ] `original_bullets` preserved for validation comparison
- [ ] Phase 11 `gap_analysis` parameter stubbed but optional

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path infra --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. If any path or class signature is missing, report a **BLOCKING ISSUE** and exit.
