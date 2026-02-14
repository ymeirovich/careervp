"""CV models for CV Tailoring (Phase 9)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class SkillLevel(str, Enum):
    """Skill proficiency levels."""

    BEGINNER = 'BEGINNER'
    INTERMEDIATE = 'INTERMEDIATE'
    ADVANCED = 'ADVANCED'
    EXPERT = 'EXPERT'


class Skill(BaseModel):
    """Skill with proficiency and optional years of experience."""

    name: str
    level: SkillLevel | None = None
    years_of_experience: int | None = None

    model_config = {'frozen': True}


class WorkExperience(BaseModel):
    """Work experience entry."""

    company: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    current: bool = False
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    dates: str | None = None

    @model_validator(mode='after')
    def _populate_dates(self) -> 'WorkExperience':
        if not self.dates:
            if self.end_date:
                self.dates = f'{self.start_date}-{self.end_date}'
            else:
                self.dates = self.start_date
        return self


class Education(BaseModel):
    """Education entry."""

    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: float | None = None
    honors: list[str] = Field(default_factory=list)
    dates: str | None = None

    @model_validator(mode='after')
    def _populate_dates(self) -> 'Education':
        if not self.dates:
            if self.end_date:
                if self.start_date:
                    self.dates = f'{self.start_date}-{self.end_date}'
                else:
                    self.dates = self.end_date
            else:
                self.dates = self.start_date
        return self


class Certification(BaseModel):
    """Certification entry."""

    name: str
    issuing_organization: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    credential_id: str | None = None


class ContactInfo(BaseModel):
    """Contact information."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None


class UserCV(BaseModel):
    """User CV model for tailoring workflow."""

    cv_id: str | None = None
    user_id: str
    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    professional_summary: str | None = None
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    contact_info: ContactInfo | None = None

    @model_validator(mode='after')
    def _populate_contact_info(self) -> 'UserCV':
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
        return self.work_experience

    @experience.setter
    def experience(self, value: list[WorkExperience]) -> None:
        self.work_experience = value

    def skill_names(self) -> list[str]:
        return [skill.name for skill in self.skills if isinstance(skill, Skill)]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
