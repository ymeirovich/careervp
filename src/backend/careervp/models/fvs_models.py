"""FVS baseline models for CV tailoring."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from careervp.models.cv_models import Certification, Skill


class ImmutableFact(BaseModel):
    """Single immutable fact extracted from master CV."""

    fact_type: str
    value: str
    context: str


class FVSBaseline(BaseModel):
    """Baseline of immutable facts for FVS validation."""

    cv_id: str
    user_id: str
    full_name: str | None = None
    immutable_facts: list[ImmutableFact] = Field(default_factory=list)
    created_at: datetime | None = None

    email: str | None = None
    phone: str | None = None
    location: str | None = None
    experience_dates: list[str] = Field(default_factory=list)
    education_dates: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    skills: list[Skill | str] = Field(default_factory=list)
    certifications: list[Certification | str] = Field(default_factory=list)
