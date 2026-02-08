"""Pydantic models for CV Tailoring (Phase 9)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_serializer, model_validator

from careervp.models.cv_models import Certification, ContactInfo, Education, Skill, WorkExperience


class TailoringPreferences(BaseModel):
    """User preferences for CV tailoring."""

    # Legacy/spec fields
    tone: str | None = 'professional'
    length: str | None = 'standard'
    emphasize_skills: list[str] = Field(default_factory=list)
    include_summary: bool = True
    max_pages: int | None = Field(default=2, ge=1)

    # Extended fields used by tests/fixtures
    target_length: str | None = None
    emphasis_areas: list[str] = Field(default_factory=list)
    include_all_experience: bool | None = None
    keyword_density: str | None = None


class TailorCVRequest(BaseModel):
    """Request to generate a tailored CV."""

    cv_id: str = Field(min_length=1)
    job_description: str = Field(min_length=20, max_length=50_000)
    user_id: str | None = None
    preferences: TailoringPreferences | None = None
    idempotency_key: str | None = None

    @model_validator(mode='after')
    def _ensure_preferences(self) -> 'TailorCVRequest':
        if self.preferences is None:
            self.preferences = TailoringPreferences()
        return self


class ChangeLog(BaseModel):
    """Represents a single change made during tailoring."""

    section: str
    change_type: str
    description: str


class TailoredCV(BaseModel):
    """Tailored CV output model."""

    cv_id: str
    user_id: str
    job_description_hash: str | None = None
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    professional_summary: str | None = None
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill | str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    contact_info: ContactInfo | None = None

    @model_validator(mode='after')
    def _populate_contact_info(self) -> 'TailoredCV':
        if self.contact_info is None:
            self.contact_info = ContactInfo(
                name=self.full_name,
                email=self.email,
                phone=self.phone,
                location=self.location,
            )
        return self

    @property
    def experience(self) -> list[WorkExperience]:
        """Alias for work_experience for backward compatibility."""
        return self.work_experience

    @experience.setter
    def experience(self, value: list[WorkExperience]) -> None:
        self.work_experience = value

    @field_serializer('skills')
    def _serialize_skills(self, skills: list[Skill | str]) -> list[str]:
        serialized: list[str] = []
        for skill in skills:
            if isinstance(skill, Skill):
                serialized.append(skill.name)
            else:
                serialized.append(str(skill))
        return serialized


class TailoredCVResponse(BaseModel):
    """Container for tailoring results and optional response metadata."""

    # Response wrapper fields
    success: bool | None = None
    error_message: str | None = None
    error_code: str | None = None
    download_url: str | None = None
    metadata: dict[str, Any] | None = None

    # Tailoring data fields
    tailored_cv: TailoredCV | None = None
    changes_made: list[ChangeLog] = Field(default_factory=list)
    relevance_scores: dict[str, float] = Field(default_factory=dict)
    average_relevance_score: float = 0.0
    keyword_matches: list[str] = Field(default_factory=list)
    estimated_ats_score: int = 0

    @model_validator(mode='after')
    def _validate_consistency(self) -> 'TailoredCVResponse':
        if self.success is True:
            if self.tailored_cv is None and self.metadata is None:
                raise ValueError('tailored_cv is required when success is True')
        if self.success is False:
            if not self.error_message:
                raise ValueError('error_message is required when success is False')
        return self
