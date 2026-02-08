"""
Pydantic models for CV parsing and validation.
Per docs/specs/01-cv-parser.md and docs/architecture/api_spec.openapi.yml.

FVS Tiers (per CLAUDE.md):
- IMMUTABLE: Dates, company names, job titles, contact info - NEVER modify
- VERIFIABLE: Skills in source CV - reframe only if source exists
- FLEXIBLE: Professional summaries - full creative liberty
"""

from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field


class ContactInfo(BaseModel):
    """Contact information - IMMUTABLE tier."""

    phone: Annotated[str | None, Field(description='Phone number')] = None
    email: Annotated[EmailStr | None, Field(description='Email address')] = None
    location: Annotated[str | None, Field(description='City, Country')] = None
    linkedin: Annotated[str | None, Field(description='LinkedIn profile URL')] = None


class WorkExperience(BaseModel):
    """Single work experience entry - dates/company/role are IMMUTABLE."""

    company: Annotated[str, Field(description='Company name - IMMUTABLE')]
    role: Annotated[str, Field(description='Job title - IMMUTABLE')]
    dates: Annotated[str, Field(description='Employment dates (e.g., "2021 – Present") - IMMUTABLE')]
    achievements: Annotated[list[str], Field(default_factory=list, description='Quantified achievements - VERIFIABLE')]


class Education(BaseModel):
    """Education entry - institution/degree/dates are IMMUTABLE."""

    institution: Annotated[str, Field(description='School/University name - IMMUTABLE')]
    degree: Annotated[str, Field(description='Degree name - IMMUTABLE')]
    field_of_study: Annotated[str | None, Field(description='Major/Field')] = None
    graduation_date: Annotated[str | None, Field(description='Graduation date - IMMUTABLE')] = None


class Certification(BaseModel):
    """Professional certification - IMMUTABLE."""

    name: Annotated[str, Field(description='Certification name')]
    issuer: Annotated[str | None, Field(description='Issuing organization')] = None
    date: Annotated[str | None, Field(description='Date obtained')] = None


class UserCV(BaseModel):
    """
    Complete CV structure extracted from user upload.
    Per OpenAPI spec: required fields are user_id, full_name, email.
    Per 01-cv-parser.md: Focus on 10 core attributes.
    """

    # Identification
    user_id: Annotated[str, Field(description='Unique user identifier')]
    full_name: Annotated[str, Field(description='Full name - IMMUTABLE')]

    # Language detection per 01-cv-parser.md
    language: Annotated[Literal['en', 'he'], Field(default='en', description='Detected language (English/Hebrew)')]

    # Contact - IMMUTABLE tier
    contact_info: Annotated[ContactInfo, Field(default_factory=ContactInfo)]

    # Work History - IMMUTABLE tier (dates, roles, companies)
    experience: Annotated[list[WorkExperience], Field(default_factory=list, description='Work history with dates')]

    # Education - IMMUTABLE tier
    education: Annotated[list[Education], Field(default_factory=list)]

    # Certifications - IMMUTABLE tier
    certifications: Annotated[list[Certification], Field(default_factory=list)]

    # Skills - VERIFIABLE tier (must exist in source CV)
    skills: Annotated[list[str], Field(default_factory=list, max_length=50, description='Technical and soft skills')]

    # Quantified achievements (top 3) - VERIFIABLE tier
    top_achievements: Annotated[list[str], Field(default_factory=list, max_length=3, description='Top 3 quantified achievements')]

    # Professional Summary - FLEXIBLE tier
    professional_summary: Annotated[str | None, Field(description='Professional summary - can be tailored')] = None

    # Parsing metadata
    is_parsed: Annotated[bool, Field(default=False, description='Whether CV has been parsed')]
    source_file_key: Annotated[str | None, Field(description='S3 key of source document')] = None


class ImmutableFacts(BaseModel):
    """
    Extracted immutable facts for FVS validation.
    Used to compare baseline CV against tailored output.
    Mirrors structure of tests/fixtures/fvs_baseline_cv.json.
    """

    contact_info: ContactInfo
    work_history: list[WorkExperience]
    education: list[Education]


class FVSBaseline(BaseModel):
    """
    FVS Baseline document for fact verification.
    Per tests/fixtures/fvs_baseline_cv.json structure.
    """

    full_name: str
    immutable_facts: ImmutableFacts
    verifiable_skills: list[str]


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
    'ContactInfo',
    'WorkExperience',
    'Education',
    'Certification',
    'UserCV',
    'ImmutableFacts',
    'FVSBaseline',
    'CVParseRequest',
    'CVParseResponse',
    'CV',
]
