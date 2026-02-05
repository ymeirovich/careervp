# Task 10.8: Pydantic Models for Cover Letters

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.1 (Validation)
**Blocking:** Task 10.3 (Logic), Task 10.4 (Prompt), Task 10.5 (FVS)
**Complexity:** Low
**Duration:** 1 hour
**Test File:** `tests/cover-letter/unit/test_cover_letter_models.py` (20-25 tests)

## Overview

Implement Pydantic models for cover letter request/response validation. These models are BLOCKING for multiple downstream tasks and should be implemented early.

## Todo

### Model Implementation

- [ ] Create `src/backend/careervp/models/cover_letter_models.py`
- [ ] Implement `GenerateCoverLetterRequest` model
- [ ] Implement `CoverLetterPreferences` model
- [ ] Implement `TailoredCoverLetter` model
- [ ] Implement `TailoredCoverLetterResponse` model
- [ ] Add field validators for constraints
- [ ] Add serialization/deserialization support

### Test Implementation

- [ ] Create `tests/cover-letter/unit/test_cover_letter_models.py`
- [ ] Test request model validation
- [ ] Test preferences defaults
- [ ] Test response serialization
- [ ] Test field constraints
- [ ] Test edge cases

---

## Codex Implementation Guide

### File Path

`src/backend/careervp/models/cover_letter_models.py`

### Key Implementation

```python
"""
Pydantic models for cover letter generation.

Per COVER_LETTER_SPEC.md API specification.
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


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
        max_length=10,
        description="Areas to emphasize (max 10)",
    )
    include_salary_expectations: bool = Field(
        default=False,
        description="Whether to include salary expectations",
    )

    @field_validator("emphasis_areas")
    @classmethod
    def validate_emphasis_areas(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate emphasis areas list."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 emphasis areas allowed")
        for area in v:
            if len(area) > 100:
                raise ValueError("Each emphasis area must be 100 characters or less")
        return v


class GenerateCoverLetterRequest(BaseModel):
    """Request model for cover letter generation."""

    cv_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="ID of the CV to use",
    )
    job_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="ID of the job posting",
    )
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Target company name",
    )
    job_title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Target job title",
    )
    preferences: Optional[CoverLetterPreferences] = Field(
        default=None,
        description="Optional generation preferences",
    )

    @field_validator("company_name", "job_title")
    @classmethod
    def validate_no_script_tags(cls, v: str) -> str:
        """Prevent XSS in company name and job title."""
        if "<script" in v.lower():
            raise ValueError("Invalid characters detected")
        return v.strip()


class TailoredCoverLetter(BaseModel):
    """Model for generated cover letter."""

    cover_letter_id: str = Field(
        ...,
        description="Unique cover letter ID",
    )
    cv_id: str = Field(
        ...,
        description="Source CV ID",
    )
    job_id: str = Field(
        ...,
        description="Target job ID",
    )
    user_id: str = Field(
        ...,
        description="Owner user ID",
    )
    company_name: str = Field(
        ...,
        description="Target company name",
    )
    job_title: str = Field(
        ...,
        description="Target job title",
    )
    content: str = Field(
        ...,
        description="Cover letter text content",
    )
    word_count: int = Field(
        ...,
        ge=0,
        description="Word count of content",
    )
    personalization_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Personalization quality score",
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance quality score",
    )
    tone_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Tone appropriateness score",
    )
    generated_at: datetime = Field(
        ...,
        description="Generation timestamp",
    )

    @property
    def overall_quality_score(self) -> float:
        """Calculate weighted overall quality score."""
        return (
            0.40 * self.personalization_score +
            0.35 * self.relevance_score +
            0.25 * self.tone_score
        )


class FVSViolationModel(BaseModel):
    """Model for FVS violation details."""

    field: str = Field(..., description="Field with violation")
    expected: str = Field(..., description="Expected value")
    actual: str = Field(..., description="Actual value found")
    severity: str = Field(..., description="Violation severity")
    message: str = Field(..., description="Human-readable message")


class FVSValidationResultModel(BaseModel):
    """Model for FVS validation result."""

    is_valid: bool = Field(..., description="Whether validation passed")
    violations: List[FVSViolationModel] = Field(
        default_factory=list,
        description="Critical violations",
    )
    warnings: List[FVSViolationModel] = Field(
        default_factory=list,
        description="Warning violations",
    )


class TailoredCoverLetterResponse(BaseModel):
    """Response model for cover letter generation."""

    success: bool = Field(
        ...,
        description="Whether generation succeeded",
    )
    cover_letter: Optional[TailoredCoverLetter] = Field(
        default=None,
        description="Generated cover letter (if success)",
    )
    fvs_validation: Optional[FVSValidationResultModel] = Field(
        default=None,
        description="FVS validation result",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall quality score",
    )
    code: str = Field(
        ...,
        description="Result code",
    )
    processing_time_ms: int = Field(
        ...,
        ge=0,
        description="Processing time in milliseconds",
    )
    cost_estimate: float = Field(
        ...,
        ge=0.0,
        description="Estimated cost in USD",
    )
    download_url: Optional[str] = Field(
        default=None,
        description="Presigned download URL",
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
```

---

## Test Implementation

### test_cover_letter_models.py

```python
"""Unit tests for cover letter Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from careervp.models.cover_letter_models import (
    CoverLetterPreferences,
    GenerateCoverLetterRequest,
    TailoredCoverLetter,
    TailoredCoverLetterResponse,
    FVSValidationResultModel,
)


class TestCoverLetterPreferences:
    """Tests for CoverLetterPreferences model."""

    def test_default_values(self):
        """Test default preference values."""
        prefs = CoverLetterPreferences()

        assert prefs.tone == "professional"
        assert prefs.word_count_target == 300
        assert prefs.emphasis_areas is None
        assert prefs.include_salary_expectations is False

    def test_valid_tone_professional(self):
        """Test professional tone is valid."""
        prefs = CoverLetterPreferences(tone="professional")
        assert prefs.tone == "professional"

    def test_valid_tone_enthusiastic(self):
        """Test enthusiastic tone is valid."""
        prefs = CoverLetterPreferences(tone="enthusiastic")
        assert prefs.tone == "enthusiastic"

    def test_valid_tone_technical(self):
        """Test technical tone is valid."""
        prefs = CoverLetterPreferences(tone="technical")
        assert prefs.tone == "technical"

    def test_invalid_tone(self):
        """Test invalid tone raises error."""
        with pytest.raises(ValidationError):
            CoverLetterPreferences(tone="casual")

    def test_word_count_minimum(self):
        """Test word count minimum boundary."""
        prefs = CoverLetterPreferences(word_count_target=200)
        assert prefs.word_count_target == 200

    def test_word_count_below_minimum(self):
        """Test word count below minimum raises error."""
        with pytest.raises(ValidationError):
            CoverLetterPreferences(word_count_target=199)

    def test_word_count_maximum(self):
        """Test word count maximum boundary."""
        prefs = CoverLetterPreferences(word_count_target=500)
        assert prefs.word_count_target == 500

    def test_word_count_above_maximum(self):
        """Test word count above maximum raises error."""
        with pytest.raises(ValidationError):
            CoverLetterPreferences(word_count_target=501)

    def test_emphasis_areas_valid(self):
        """Test valid emphasis areas."""
        prefs = CoverLetterPreferences(emphasis_areas=["python", "aws"])
        assert prefs.emphasis_areas == ["python", "aws"]

    def test_emphasis_areas_too_many(self):
        """Test too many emphasis areas raises error."""
        with pytest.raises(ValidationError):
            CoverLetterPreferences(emphasis_areas=["a"] * 11)


class TestGenerateCoverLetterRequest:
    """Tests for GenerateCoverLetterRequest model."""

    def test_valid_request(self):
        """Test valid request creation."""
        request = GenerateCoverLetterRequest(
            cv_id="cv_123",
            job_id="job_456",
            company_name="TechCorp",
            job_title="Engineer",
        )

        assert request.cv_id == "cv_123"
        assert request.job_id == "job_456"

    def test_request_with_preferences(self):
        """Test request with preferences."""
        request = GenerateCoverLetterRequest(
            cv_id="cv_123",
            job_id="job_456",
            company_name="TechCorp",
            job_title="Engineer",
            preferences=CoverLetterPreferences(tone="technical"),
        )

        assert request.preferences.tone == "technical"

    def test_empty_cv_id(self):
        """Test empty cv_id raises error."""
        with pytest.raises(ValidationError):
            GenerateCoverLetterRequest(
                cv_id="",
                job_id="job_456",
                company_name="TechCorp",
                job_title="Engineer",
            )

    def test_company_name_xss_prevention(self):
        """Test XSS prevention in company name."""
        with pytest.raises(ValidationError):
            GenerateCoverLetterRequest(
                cv_id="cv_123",
                job_id="job_456",
                company_name="<script>alert('xss')</script>",
                job_title="Engineer",
            )

    def test_company_name_strips_whitespace(self):
        """Test company name strips whitespace."""
        request = GenerateCoverLetterRequest(
            cv_id="cv_123",
            job_id="job_456",
            company_name="  TechCorp  ",
            job_title="Engineer",
        )

        assert request.company_name == "TechCorp"


class TestTailoredCoverLetter:
    """Tests for TailoredCoverLetter model."""

    def test_valid_cover_letter(self):
        """Test valid cover letter creation."""
        letter = TailoredCoverLetter(
            cover_letter_id="cl_123",
            cv_id="cv_456",
            job_id="job_789",
            user_id="user_abc",
            company_name="TechCorp",
            job_title="Engineer",
            content="Cover letter content here",
            word_count=300,
            personalization_score=0.8,
            relevance_score=0.8,
            tone_score=0.8,
            generated_at=datetime.now(),
        )

        assert letter.cover_letter_id == "cl_123"

    def test_overall_quality_score(self):
        """Test overall quality score calculation."""
        letter = TailoredCoverLetter(
            cover_letter_id="cl_123",
            cv_id="cv_456",
            job_id="job_789",
            user_id="user_abc",
            company_name="TechCorp",
            job_title="Engineer",
            content="Content",
            word_count=300,
            personalization_score=1.0,
            relevance_score=1.0,
            tone_score=1.0,
            generated_at=datetime.now(),
        )

        assert letter.overall_quality_score == 1.0

    def test_quality_score_weights(self):
        """Test quality score weights are correct."""
        letter = TailoredCoverLetter(
            cover_letter_id="cl_123",
            cv_id="cv_456",
            job_id="job_789",
            user_id="user_abc",
            company_name="TechCorp",
            job_title="Engineer",
            content="Content",
            word_count=300,
            personalization_score=0.5,
            relevance_score=0.5,
            tone_score=0.5,
            generated_at=datetime.now(),
        )

        # 0.40 * 0.5 + 0.35 * 0.5 + 0.25 * 0.5 = 0.5
        assert letter.overall_quality_score == 0.5

    def test_score_out_of_range(self):
        """Test score out of range raises error."""
        with pytest.raises(ValidationError):
            TailoredCoverLetter(
                cover_letter_id="cl_123",
                cv_id="cv_456",
                job_id="job_789",
                user_id="user_abc",
                company_name="TechCorp",
                job_title="Engineer",
                content="Content",
                word_count=300,
                personalization_score=1.5,  # Invalid
                relevance_score=0.8,
                tone_score=0.8,
                generated_at=datetime.now(),
            )


class TestTailoredCoverLetterResponse:
    """Tests for TailoredCoverLetterResponse model."""

    def test_success_response(self):
        """Test successful response creation."""
        response = TailoredCoverLetterResponse(
            success=True,
            quality_score=0.85,
            code="COVER_LETTER_GENERATED_SUCCESS",
            processing_time_ms=5000,
            cost_estimate=0.005,
        )

        assert response.success is True

    def test_error_response(self):
        """Test error response creation."""
        response = TailoredCoverLetterResponse(
            success=False,
            quality_score=0.0,
            code="CV_NOT_FOUND",
            processing_time_ms=100,
            cost_estimate=0.0,
        )

        assert response.success is False

    def test_json_serialization(self):
        """Test response JSON serialization."""
        response = TailoredCoverLetterResponse(
            success=True,
            quality_score=0.85,
            code="SUCCESS",
            processing_time_ms=5000,
            cost_estimate=0.005,
        )

        json_dict = response.model_dump(mode="json")
        assert "success" in json_dict
        assert "quality_score" in json_dict
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format
uv run ruff format careervp/models/cover_letter_models.py

# Lint
uv run ruff check --fix careervp/models/cover_letter_models.py

# Type check
uv run mypy careervp/models/cover_letter_models.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_cover_letter_models.py -v

# Expected: 27 tests PASSED
```

---

## Completion Criteria

- [ ] All Pydantic models implemented
- [ ] Field validators working
- [ ] XSS prevention in company_name/job_title
- [ ] Quality score calculation correct
- [ ] JSON serialization working
- [ ] All 27 tests passing
- [ ] ruff format passes
- [ ] mypy --strict passes

---

## References

- [COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md) - Model definitions
- [cv_models.py](../../../src/backend/careervp/models/) - Pattern reference
