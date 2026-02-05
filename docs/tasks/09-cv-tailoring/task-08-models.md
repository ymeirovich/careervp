# Task 9.8: CV Tailoring - Pydantic Models

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** None (but before any tailoring code)
**Blocking:** Task 9.1, Task 9.3, Task 9.6

## Overview

Implement Pydantic models for CV tailoring including request/response schemas, tailored CV structure, and supporting types. All models follow FVS tier classification system (IMMUTABLE, VERIFIABLE, FLEXIBLE) and support optional gap_analysis parameter for Phase 11 extensibility.

## Todo

### Models Implementation

- [ ] Create `src/backend/careervp/models/tailor.py` (if not already created in Task 9.1)
- [ ] Implement `StylePreferences` model for output customization
- [ ] Implement `TailorCVRequest` model for API input validation
- [ ] Implement `TailoredSkill` model with relevance scoring
- [ ] Implement `TailoredWorkExperience` model with IMMUTABLE/FLEXIBLE separation
- [ ] Implement `TailoredCV` model as main output structure
- [ ] Implement `TailoringMetadata` model for tracking modifications
- [ ] Implement `TailoredCVData` model combining CV and metadata
- [ ] Implement `TailorCVResponse` model for API response
- [ ] Update `src/backend/careervp/models/__init__.py` with exports

### Test Implementation

- [ ] Create `tests/models/test_tailoring_models.py`
- [ ] Implement 20-25 test cases covering all models
- [ ] Test model validation (4 tests)
- [ ] Test serialization/deserialization (4 tests)
- [ ] Test FVS tier field annotations (4 tests)
- [ ] Test request/response models (4 tests)
- [ ] Test optional fields and defaults (4 tests)

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/models/`
- [ ] Run `uv run ruff check --fix src/backend/careervp/models/`
- [ ] Run `uv run mypy src/backend/careervp/models/ --strict`
- [ ] Run `uv run pytest tests/models/test_tailoring_models.py -v`

### Commit

- [ ] Commit with message: `feat(models): add CV tailoring Pydantic models with FVS tier annotations`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/models/tailor.py` | All CV tailoring models |
| `tests/models/test_tailoring_models.py` | Comprehensive model tests |
| `src/backend/careervp/models/__init__.py` | Export new models |

### Key Implementation Details

```python
"""
Pydantic Models for CV Tailoring.
Per docs/specs/04-cv-tailoring.md.

FVS Tier Classification:
- IMMUTABLE: Cannot be altered (dates, titles, company names, degrees)
- VERIFIABLE: Must exist in source CV (skills, certifications)
- FLEXIBLE: Can be creatively reframed (summaries, bullet descriptions)

All models support JSON serialization for API responses and DynamoDB storage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, validator


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

    class Config:
        """Pydantic config for request model."""
        json_schema_extra = {
            'example': {
                'user_id': 'user_123',
                'application_id': 'app_456',
                'job_id': 'job_789',
                'cv_version': 1,
                'include_gap_analysis': False,
                'style_preferences': {
                    'tone': 'professional',
                    'formality_level': 'high',
                },
            }
        }


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

    # FVS_COMMENT: IMMUTABLE - contact info copied directly
    contact_info: Annotated[
        dict[str, str | None],
        Field(description='IMMUTABLE - Contact details from source CV'),
    ]

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
    user_id: Annotated[str, Field(description='User identifier')]
    job_id: Annotated[str, Field(description='Target job identifier')]
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

    class Config:
        """Pydantic config for response model."""
        json_schema_extra = {
            'example': {
                'success': True,
                'code': 'CV_TAILORED',
                'data': {
                    'tailored_cv': {},
                    'metadata': {},
                    'token_usage': {},
                },
            }
        }
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

### Test Implementation Structure

```python
"""
Tests for CV Tailoring Models.
Per tests/models/test_tailoring_models.py.

Test categories:
- Model validation (4 tests)
- Serialization/deserialization (4 tests)
- FVS tier annotations (4 tests)
- Request/response models (4 tests)
- Optional fields and defaults (4 tests)

Total: 20-25 tests
"""

import pytest
import json
from datetime import datetime

from careervp.models.tailor import (
    StylePreferences,
    TailorCVRequest,
    TailoredSkill,
    TailoredWorkExperience,
    TailoredCV,
    TailoringMetadata,
    TokenUsage,
    TailoredCVData,
    TailorCVResponse,
)


class TestStylePreferences:
    """Test StylePreferences model."""

    def test_style_preferences_default_values(self):
        """StylePreferences has sensible defaults."""
        # PSEUDO-CODE:
        # prefs = StylePreferences()
        # assert prefs.tone == 'professional'
        # assert prefs.formality_level == 'high'
        # assert prefs.include_summary is True
        pass

    def test_style_preferences_custom_values(self):
        """StylePreferences accepts custom values."""
        # PSEUDO-CODE:
        # prefs = StylePreferences(
        #     tone='technical',
        #     formality_level='low',
        #     include_summary=False,
        # )
        # assert prefs.tone == 'technical'
        pass

    def test_style_preferences_invalid_tone(self):
        """StylePreferences validates tone enum."""
        # PSEUDO-CODE:
        # with pytest.raises(ValidationError):
        #     StylePreferences(tone='invalid')
        pass

    def test_style_preferences_serialization(self):
        """StylePreferences serializes correctly."""
        # PSEUDO-CODE:
        # prefs = StylePreferences(tone='conversational')
        # json_str = prefs.model_dump_json()
        # assert 'conversational' in json_str
        pass


class TestTailorCVRequest:
    """Test TailorCVRequest model."""

    def test_request_required_fields(self):
        """TailorCVRequest requires user_id, application_id, job_id."""
        # PSEUDO-CODE:
        # with pytest.raises(ValidationError):
        #     TailorCVRequest()  # Missing required fields
        pass

    def test_request_valid_creation(self):
        """TailorCVRequest accepts valid data."""
        # PSEUDO-CODE:
        # request = TailorCVRequest(
        #     user_id='user_123',
        #     application_id='app_456',
        #     job_id='job_789',
        # )
        # assert request.user_id == 'user_123'
        # assert request.cv_version == 1  # Default
        pass

    def test_request_cv_version_validation(self):
        """TailorCVRequest validates cv_version >= 1."""
        # PSEUDO-CODE:
        # with pytest.raises(ValidationError):
        #     TailorCVRequest(
        #         user_id='u',
        #         application_id='a',
        #         job_id='j',
        #         cv_version=0,  # Invalid
        #     )
        pass

    def test_request_with_gap_analysis_optional(self):
        """TailorCVRequest gap_analysis is optional."""
        # PSEUDO-CODE:
        # request = TailorCVRequest(user_id='u', application_id='a', job_id='j')
        # assert request.include_gap_analysis is False  # Default
        pass


class TestTailoredSkill:
    """Test TailoredSkill model."""

    def test_skill_relevance_score_validation(self):
        """TailoredSkill validates relevance_score 0.0-1.0."""
        # PSEUDO-CODE:
        # skill = TailoredSkill(skill_name='Python', relevance_score=0.75)
        # assert skill.relevance_score == 0.75
        # 
        # with pytest.raises(ValidationError):
        #     TailoredSkill(skill_name='Python', relevance_score=1.5)
        pass

    def test_skill_matched_requirements_optional(self):
        """TailoredSkill matched_requirements is optional."""
        # PSEUDO-CODE:
        # skill = TailoredSkill(skill_name='AWS', relevance_score=0.8)
        # assert skill.matched_requirements == []
        pass

    def test_skill_fvs_annotation_present(self):
        """TailoredSkill has FVS annotation in description."""
        # PSEUDO-CODE:
        # field = TailoredSkill.model_fields['skill_name']
        # assert 'VERIFIABLE' in field.description
        pass

    def test_skill_serialization(self):
        """TailoredSkill serializes to JSON."""
        # PSEUDO-CODE:
        # skill = TailoredSkill(
        #     skill_name='Python',
        #     relevance_score=0.9,
        #     matched_requirements=['Python'],
        # )
        # json_str = skill.model_dump_json()
        # data = json.loads(json_str)
        # assert data['skill_name'] == 'Python'
        pass


class TestTailoredWorkExperience:
    """Test TailoredWorkExperience model."""

    def test_experience_immutable_fields_required(self):
        """TailoredWorkExperience requires IMMUTABLE fields."""
        # PSEUDO-CODE:
        # with pytest.raises(ValidationError):
        #     TailoredWorkExperience()  # Missing required fields
        pass

    def test_experience_immutable_fvs_annotation(self):
        """TailoredWorkExperience has IMMUTABLE annotations."""
        # PSEUDO-CODE:
        # for field_name in ['company_name', 'job_title', 'start_date']:
        #     field = TailoredWorkExperience.model_fields[field_name]
        #     assert 'IMMUTABLE' in field.description
        pass

    def test_experience_flexible_fvs_annotation(self):
        """TailoredWorkExperience has FLEXIBLE annotations."""
        # PSEUDO-CODE:
        # field = TailoredWorkExperience.model_fields['description_bullets']
        # assert 'FLEXIBLE' in field.description
        pass

    def test_experience_original_bullets_preserved(self):
        """TailoredWorkExperience preserves original_bullets."""
        # PSEUDO-CODE:
        # exp = TailoredWorkExperience(
        #     company_name='Acme',
        #     job_title='Engineer',
        #     start_date='2020-01-01',
        #     description_bullets=['New bullet'],
        #     original_bullets=['Old bullet'],
        # )
        # assert exp.original_bullets == ['Old bullet']
        pass


class TestTailoredCV:
    """Test TailoredCV model."""

    def test_cv_contact_info_immutable_annotation(self):
        """TailoredCV contact_info has IMMUTABLE annotation."""
        # PSEUDO-CODE:
        # field = TailoredCV.model_fields['contact_info']
        # assert 'IMMUTABLE' in field.description
        pass

    def test_cv_executive_summary_flexible_annotation(self):
        """TailoredCV executive_summary has FLEXIBLE annotation."""
        # PSEUDO-CODE:
        # field = TailoredCV.model_fields['executive_summary']
        # assert 'FLEXIBLE' in field.description
        pass

    def test_cv_skills_verifiable_annotation(self):
        """TailoredCV skills have VERIFIABLE annotation."""
        # PSEUDO-CODE:
        # field = TailoredCV.model_fields['skills']
        # assert 'VERIFIABLE' in field.description
        pass

    def test_cv_serialization(self):
        """TailoredCV serializes to JSON."""
        # PSEUDO-CODE:
        # cv = TailoredCV(
        #     contact_info={},
        #     executive_summary='Summary',
        #     work_experience=[],
        #     skills=[],
        #     education=[],
        #     source_cv_version=1,
        #     target_job_id='job_123',
        # )
        # json_str = cv.model_dump_json()
        # assert 'Summary' in json_str
        pass


class TestTailoringMetadata:
    """Test TailoringMetadata model."""

    def test_metadata_created_at_datetime(self):
        """TailoringMetadata created_at is datetime."""
        # PSEUDO-CODE:
        # now = datetime.utcnow()
        # metadata = TailoringMetadata(
        #     application_id='app_123',
        #     user_id='user_123',
        #     job_id='job_123',
        #     version=1,
        #     created_at=now,
        #     keyword_matches=10,
        #     sections_modified=['summary'],
        #     fvs_validation_passed=True,
        # )
        # assert isinstance(metadata.created_at, datetime)
        pass

    def test_metadata_sections_modified_optional(self):
        """TailoringMetadata sections_modified optional."""
        # PSEUDO-CODE:
        # metadata = TailoringMetadata(
        #     application_id='app_123',
        #     user_id='user_123',
        #     job_id='job_123',
        #     version=1,
        #     created_at=datetime.utcnow(),
        #     keyword_matches=5,
        #     sections_modified=[],
        #     fvs_validation_passed=False,
        # )
        # assert metadata.sections_modified == []
        pass

    def test_metadata_serialization(self):
        """TailoringMetadata serializes to JSON with ISO datetime."""
        # PSEUDO-CODE:
        # metadata = TailoringMetadata(...)
        # json_str = metadata.model_dump_json()
        # data = json.loads(json_str)
        # assert 'created_at' in data
        pass

    def test_metadata_deserialization(self):
        """TailoringMetadata deserializes from JSON."""
        # PSEUDO-CODE:
        # json_str = '{"application_id":"app_123",...}'
        # metadata = TailoringMetadata.model_validate_json(json_str)
        # assert metadata.application_id == 'app_123'
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format src/backend/careervp/models/

# Check for style issues
uv run ruff check --fix src/backend/careervp/models/

# Type check with strict mode
uv run mypy src/backend/careervp/models/ --strict

# Run model tests
uv run pytest tests/models/test_tailoring_models.py -v

# Expected output:
# ===== test session starts =====
# tests/models/test_tailoring_models.py::TestStylePreferences PASSED (4 tests)
# tests/models/test_tailoring_models.py::TestTailorCVRequest PASSED (4 tests)
# ... [20-25 total tests]
# ===== 20-25 passed in X.XXs =====
```

### Expected Test Results

```
tests/models/test_tailoring_models.py PASSED

Model Validation: 4 PASSED
- Required fields enforced
- Enum validation working
- Number ranges validated
- Field constraints respected

Serialization/Deserialization: 4 PASSED
- Models serialize to JSON
- Models deserialize from JSON
- DateTime handling correct
- Round-trip preserves data

FVS Tier Annotations: 4 PASSED
- IMMUTABLE fields marked
- VERIFIABLE fields marked
- FLEXIBLE fields marked
- Annotations readable in descriptions

Request/Response Models: 4 PASSED
- TailorCVRequest validates correctly
- TailorCVResponse formats correctly
- Default values set appropriately
- Optional fields handled

Optional Fields and Defaults: 4 PASSED
- Defaults apply correctly
- Optional fields omitted when None
- Lists default to empty
- Booleans default correctly

Total: 20-25 tests passing
Type checking: 0 errors, 0 warnings
JSON Schema: Valid and complete
```

### Zero-Hallucination Checklist

- [ ] All IMMUTABLE fields have "IMMUTABLE" in description
- [ ] All VERIFIABLE fields have "VERIFIABLE" in description
- [ ] All FLEXIBLE fields have "FLEXIBLE" in description
- [ ] TailoredWorkExperience includes original_bullets for validation
- [ ] No default values for IMMUTABLE fields
- [ ] include_gap_analysis parameter exists for Phase 11
- [ ] All models use Annotated for type hints
- [ ] Field descriptions are complete and accurate
- [ ] Models support JSON serialization
- [ ] FVS tier classifications match specification

### Acceptance Criteria

- [ ] All models pass `mypy --strict` validation
- [ ] Models follow existing patterns in `cv.py` and `vpr.py`
- [ ] FVS tier classifications documented in Field descriptions
- [ ] `original_bullets` preserved for validation comparison
- [ ] Phase 11 `gap_analysis` parameter optional and stubbed
- [ ] Request/Response models match API schema
- [ ] JSON serialization/deserialization working
- [ ] 20-25 tests all passing
- [ ] Models exported in `__init__.py`
- [ ] Type checking passes with `mypy --strict`

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path src/backend/careervp/models --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. Run `uv run pytest tests/models/test_tailoring_models.py -v --cov`
4. If any model is incorrect, report a **BLOCKING ISSUE** and exit.
