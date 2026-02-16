"""FVS (Fact Verification System) models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from careervp.models.cv import Certification, Skill


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


class GrammarIssue(BaseModel):
    """Grammar issue detected during FVS quality checks."""

    message: str
    suggestion: str | None = None


class ToneIssue(BaseModel):
    """Tone issue detected during FVS quality checks."""

    message: str
    recommendation: str | None = None


class QualityScore(BaseModel):
    """Detailed quality scores for FVS validation dimensions."""

    grammar_score: float = Field(ge=0.0, le=10.0)
    tone_score: float = Field(ge=0.0, le=10.0)
    ai_pattern_score: float = Field(ge=0.0, le=10.0)
    formatting_score: float = Field(ge=0.0, le=10.0)
    structure_score: float = Field(ge=0.0, le=10.0)

    @property
    def overall_score(self) -> float:
        return (self.grammar_score + self.tone_score + self.ai_pattern_score + self.formatting_score + self.structure_score) / 5.0


class FVSResult(BaseModel):
    """Aggregate FVS quality result."""

    overall_score: float = Field(ge=0.0, le=10.0)
    quality_score: QualityScore
    grammar_issues: list[GrammarIssue] = Field(default_factory=list)
    tone_issues: list[ToneIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ImmutableFact(BaseModel):
    """Single immutable fact extracted from master CV."""

    fact_type: str
    value: str
    context: str


class FVSBaseline(BaseModel):
    """Baseline of immutable facts for FVS validation."""

    cv_id: str | None = None
    user_id: str
    full_name: str | None = None
    immutable_facts: list[ImmutableFact] = Field(default_factory=list)
    created_at: datetime | None = None

    email: str | None = None
    phone: str | None = None
    location: str | None = None
    experience_dates: list[str | None] = Field(default_factory=list)
    education_dates: list[str | None] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    skills: list[Skill | str] = Field(default_factory=list)
    certifications: list[Certification | str] = Field(default_factory=list)
