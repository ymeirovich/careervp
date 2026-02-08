"""FVS (Fact Verification System) models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from careervp.models.cv import Certification, ContactInfo, Education, Skill, WorkExperience


class ViolationSeverity(str, Enum):
    """Severity levels for FVS violations."""

    CRITICAL = 'CRITICAL'
    WARNING = 'WARNING'
    INFO = 'INFO'


class FVSViolation(BaseModel):
    """Represents a single FVS violation."""

    field: str
    severity: ViolationSeverity
    expected: Any | None = None
    actual: Any | None = None


class FVSValidationResult(BaseModel):
    """Result of FVS validation."""

    violations: list[FVSViolation]

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == ViolationSeverity.CRITICAL for v in self.violations)


class ImmutableFact(BaseModel):
    """Single immutable fact extracted from master CV."""

    fact_type: str
    value: str
    context: str


class ImmutableFacts(BaseModel):
    """
    Extracted immutable facts for FVS validation.
    Mirrors structure of tests/fixtures/fvs_baseline_cv.json.
    """

    contact_info: ContactInfo
    work_history: list[WorkExperience]
    education: list[Education]


class FVSBaseline(BaseModel):
    """
    Unified FVS baseline for CV tailoring and validation.
    Supports both structured immutable facts and flat immutable fact lists.
    """

    # Tailoring baseline fields
    cv_id: str | None = None
    user_id: str | None = None
    full_name: str | None = None
    immutable_facts: list[ImmutableFact] | ImmutableFacts = Field(default_factory=list)
    created_at: datetime | None = None

    email: str | None = None
    phone: str | None = None
    location: str | None = None
    experience_dates: list[str] = Field(default_factory=list)
    education_dates: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    skills: list[Skill | str] = Field(default_factory=list)
    certifications: list[Certification | str] = Field(default_factory=list)

    # Structured baseline fields (for FVS validation)
    verifiable_skills: list[str] = Field(default_factory=list)


__all__ = [
    'ViolationSeverity',
    'FVSViolation',
    'FVSValidationResult',
    'ImmutableFact',
    'ImmutableFacts',
    'FVSBaseline',
]
