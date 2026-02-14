"""
Pydantic models for CV parsing and validation.
Per docs/specs/01-cv-parser.md and docs/architecture/api_spec.openapi.yml.

FVS Tiers (per CLAUDE.md):
- IMMUTABLE: Dates, company names, job titles, contact info - NEVER modify
- VERIFIABLE: Skills in source CV - reframe only if source exists
- FLEXIBLE: Professional summaries - full creative liberty
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_serializer, model_validator


class SkillLevel(str, Enum):
    """Skill proficiency levels."""

    BEGINNER = 'BEGINNER'
    INTERMEDIATE = 'INTERMEDIATE'
    ADVANCED = 'ADVANCED'
    EXPERT = 'EXPERT'


class CVSection(str, Enum):
    """Supported CV sections."""

    PROFESSIONAL_SUMMARY = 'professional_summary'
    WORK_EXPERIENCE = 'work_experience'
    EDUCATION = 'education'
    SKILLS = 'skills'
    CERTIFICATIONS = 'certifications'
    LANGUAGES = 'languages'


class Skill(BaseModel):
    """Skill with proficiency and optional years of experience."""

    name: str
    level: SkillLevel | None = None
    years_of_experience: int | None = None

    model_config = {'frozen': True}


class ContactInfo(BaseModel):
    """Contact information - IMMUTABLE tier."""

    name: Annotated[str | None, Field(description='Full name')] = None
    phone: Annotated[str | None, Field(description='Phone number')] = None
    email: Annotated[EmailStr | None, Field(description='Email address')] = None
    location: Annotated[str | None, Field(description='City, Country')] = None
    linkedin: Annotated[str | None, Field(description='LinkedIn profile URL')] = None


class WorkExperience(BaseModel):
    """Single work experience entry - dates/company/role are IMMUTABLE."""

    company: Annotated[str, Field(description='Company name - IMMUTABLE')]
    role: Annotated[str, Field(description='Job title - IMMUTABLE')]
    dates: Annotated[str | None, Field(description='Employment dates (e.g., "2021 – Present") - IMMUTABLE')] = None
    start_date: Annotated[str | None, Field(description='Employment start date')] = None
    end_date: Annotated[str | None, Field(description='Employment end date')] = None
    current: Annotated[bool, Field(description='Whether this is the current role')] = False
    description: Annotated[str | None, Field(description='Role description')] = None
    achievements: Annotated[list[str], Field(default_factory=list, description='Quantified achievements - VERIFIABLE')]
    technologies: Annotated[list[str], Field(default_factory=list, description='Technologies used')]

    @model_validator(mode='after')
    def _populate_dates(self) -> 'WorkExperience':
        if not self.dates:
            if self.end_date:
                self.dates = f'{self.start_date}-{self.end_date}' if self.start_date else self.end_date
            else:
                self.dates = self.start_date
        return self


class Education(BaseModel):
    """Education entry - institution/degree/dates are IMMUTABLE."""

    institution: Annotated[str, Field(description='School/University name - IMMUTABLE')]
    degree: Annotated[str, Field(description='Degree name - IMMUTABLE')]
    field_of_study: Annotated[str | None, Field(description='Major/Field')] = None
    graduation_date: Annotated[str | None, Field(description='Graduation date - IMMUTABLE')] = None
    start_date: Annotated[str | None, Field(description='Start date')] = None
    end_date: Annotated[str | None, Field(description='End date')] = None
    gpa: Annotated[float | None, Field(description='GPA')] = None
    honors: Annotated[list[str], Field(default_factory=list, description='Honors')]
    dates: Annotated[str | None, Field(description='Education dates')] = None

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
    """Professional certification - IMMUTABLE."""

    name: Annotated[str, Field(description='Certification name')]
    issuer: Annotated[str | None, Field(description='Issuing organization')] = None
    issuing_organization: Annotated[str | None, Field(description='Issuing organization (alias)')] = None
    date: Annotated[str | None, Field(description='Date obtained')] = None
    issue_date: Annotated[str | None, Field(description='Issue date')] = None
    expiry_date: Annotated[str | None, Field(description='Expiry date')] = None
    credential_id: Annotated[str | None, Field(description='Credential ID')] = None

    @model_validator(mode='after')
    def _sync_issuer_fields(self) -> 'Certification':
        if self.issuing_organization and not self.issuer:
            self.issuer = self.issuing_organization
        if self.issuer and not self.issuing_organization:
            self.issuing_organization = self.issuer
        if self.issue_date is None and self.date is not None:
            self.issue_date = self.date
        if self.date is None and self.issue_date is not None:
            self.date = self.issue_date
        return self


class UserCV(BaseModel):
    """
    Complete CV structure extracted from user upload.
    Per OpenAPI spec: required fields are user_id, full_name, email.
    Per 01-cv-parser.md: Focus on 10 core attributes.
    """

    # Identification
    user_id: Annotated[str, Field(description='Unique user identifier')]
    full_name: Annotated[str, Field(description='Full name - IMMUTABLE')]
    cv_id: Annotated[str | None, Field(description='CV identifier')] = None

    # Language detection per 01-cv-parser.md
    language: Annotated[Literal['en', 'he'], Field(default='en', description='Detected language (English/Hebrew)')]

    # Contact - IMMUTABLE tier
    contact_info: Annotated[ContactInfo | None, Field(default_factory=ContactInfo)]
    email: Annotated[EmailStr | None, Field(description='Email address')] = None
    phone: Annotated[str | None, Field(description='Phone number')] = None
    location: Annotated[str | None, Field(description='Location')] = None
    linkedin: Annotated[str | None, Field(description='LinkedIn profile URL')] = None

    # Work History - IMMUTABLE tier (dates, roles, companies)
    experience: Annotated[
        list[WorkExperience],
        Field(default_factory=list, description='Work history with dates', alias='work_experience'),
    ]

    # Education - IMMUTABLE tier
    education: Annotated[list[Education], Field(default_factory=list)]

    # Certifications - IMMUTABLE tier
    certifications: Annotated[list[Certification], Field(default_factory=list)]

    # Skills - VERIFIABLE tier (must exist in source CV)
    skills: Annotated[
        list[Skill | str],
        Field(default_factory=list, max_length=50, description='Technical and soft skills'),
    ]

    # Quantified achievements (top 3) - VERIFIABLE tier
    top_achievements: Annotated[
        list[str],
        Field(default_factory=list, max_length=3, description='Top 3 quantified achievements'),
    ]

    # Professional Summary - FLEXIBLE tier
    professional_summary: Annotated[str | None, Field(description='Professional summary - can be tailored')] = None

    # Additional metadata used by CV tailoring
    languages: Annotated[list[str], Field(default_factory=list, description='Spoken languages')]
    created_at: Annotated[datetime | None, Field(description='Created timestamp')] = None
    updated_at: Annotated[datetime | None, Field(description='Updated timestamp')] = None

    # Parsing metadata
    is_parsed: Annotated[bool, Field(default=False, description='Whether CV has been parsed')]
    source_file_key: Annotated[str | None, Field(description='S3 key of source document')] = None

    model_config = {'populate_by_name': True}

    @model_validator(mode='after')
    def _sync_contact_info(self) -> 'UserCV':
        self._ensure_contact_info()
        self._sync_from_self_to_contact()
        self._sync_from_contact_to_self()
        return self

    def _ensure_contact_info(self) -> None:
        """Create ContactInfo if None."""
        if self.contact_info is None:
            self.contact_info = ContactInfo()

    def _sync_from_self_to_contact(self) -> None:
        """Copy from self fields to contact_info (only if contact_info empty)."""
        contact = self.contact_info
        if contact is None:
            return
        if self.email and not contact.email:
            contact.email = self.email
        if self.phone and not contact.phone:
            contact.phone = self.phone
        if self.location and not contact.location:
            contact.location = self.location
        if self.linkedin and not contact.linkedin:
            contact.linkedin = self.linkedin
        if self.full_name and not contact.name:
            contact.name = self.full_name

    def _sync_from_contact_to_self(self) -> None:
        """Copy from contact_info to self fields (if self field empty)."""
        contact = self.contact_info
        if contact is None:
            return
        if not self.email and contact.email:
            self.email = contact.email
        if not self.phone and contact.phone:
            self.phone = contact.phone
        if not self.location and contact.location:
            self.location = contact.location
        if not self.linkedin and contact.linkedin:
            self.linkedin = contact.linkedin

    @property
    def work_experience(self) -> list[WorkExperience]:
        return self.experience

    @work_experience.setter
    def work_experience(self, value: list[WorkExperience]) -> None:
        self.experience = value

    def skill_names(self) -> list[str]:
        return [skill.name if isinstance(skill, Skill) else str(skill) for skill in self.skills]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @field_serializer('skills')
    def _serialize_skills(self, skills: list[Skill | str]) -> list[str]:
        serialized: list[str] = []
        for skill in skills:
            if isinstance(skill, Skill):
                serialized.append(skill.name)
            else:
                serialized.append(str(skill))
        return serialized


class CVParseRequest(BaseModel):
    """Request model for CV parsing endpoint."""

    user_id: Annotated[str, Field(description='User ID to associate CV with')]
    file_content: Annotated[str | None, Field(description='Base64 encoded file content')] = None
    text_content: Annotated[str | None, Field(description='Plain text CV content')] = None
    file_type: Annotated[Literal['pdf', 'docx', 'txt'] | None, Field(description='File type if file_content provided')] = None


class CVParseResponse(BaseModel):
    """Response model for CV parsing endpoint."""

    success: bool
    user_cv: UserCV | None = None
    language_detected: Literal['en', 'he'] = 'en'
    parse_time_ms: int = 0
    error: str | None = None


# Backward compatibility alias for tests expecting CV in this module.
CV = UserCV

__all__ = [
    'CVSection',
    'ContactInfo',
    'WorkExperience',
    'Education',
    'Certification',
    'UserCV',
    'Skill',
    'SkillLevel',
    'CVParseRequest',
    'CVParseResponse',
    'CV',
]
