"""Pydantic models for CV Tailoring (Phase 9)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer, model_validator

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
    vpr_id: str | None = None
    # When present, CV tailoring fetches this VPR and uses it as a
    # strategic guide. Optional — graceful degradation when absent.

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


# CV Sections — structured output for P1
class CVContactSection(BaseModel):
    """Contact information section for CV."""

    name: str
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    location: str | None = None


# Alias for test compatibility
CVContact = CVContactSection


class CVSkillsSection(BaseModel):
    """Skills section for CV."""

    technical: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)


# Alias for test compatibility
CVSkills = CVSkillsSection


class CVExperienceSection(BaseModel):
    """Work experience entry for CV."""

    company: str
    title: str
    start_date: str  # MM/YYYY format
    end_date: str | None = None
    is_current: bool = False
    bullets: list[str] = Field(default_factory=list)  # CAR format: "Action + Context + Result"
    location: str | None = None


# Alias for test compatibility
CVExperienceItem = CVExperienceSection


class CVEducationSection(BaseModel):
    """Education entry for CV."""

    institution: str
    degree: str
    field: str
    graduation_date: str  # MM/YYYY format
    gpa: str | None = None


class CVCertificationSection(BaseModel):
    """Certification entry for CV."""

    name: str
    issuer: str
    date: str  # MM/YYYY format


class CVSections(BaseModel):
    """Structured CV content section — P1 spec contract."""

    contact: CVContactSection
    summary: str = Field(min_length=50, max_length=600)
    skills: CVSkillsSection
    experience: list[CVExperienceSection] = Field(min_length=1)
    education: list[CVEducationSection] = Field(default_factory=list)
    certifications: list[CVCertificationSection] = Field(default_factory=list)
    languages: list[str] | None = None


class TailoredCV(BaseModel):
    """Tailored CV output model."""

    cv_id: str | None = None
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


class ATSIssue(BaseModel):
    """An issue surfaced by ATS scoring."""

    code: str
    severity: str  # "critical", "warning", "info"
    message: str
    suggestion: str


# P2: Three-Stage Pipeline Models
class PrimaryKeyword(BaseModel):
    """A keyword with evidence mapping from Stage 1."""

    keyword: str
    category: str  # "required", "preferred", "nice_to_have"
    priority: int
    supporting_evidence: str | None = None


class ExperienceItemInPlan(BaseModel):
    """Experience item selected for CV in Stage 1."""

    company: str
    title: str
    include_reason: str | None = None


class Stage1Output(BaseModel):
    """Stage 1: Keyword mapping output (Python, no LLM call)."""

    uvp_statement: str
    key_differentiators: list[str]
    primary_keywords: list[PrimaryKeyword]
    keywords_to_emphasize: list[str]
    keywords_missing_from_cv: list[str]
    experience_items_to_include: list[ExperienceItemInPlan]
    experience_items_to_exclude: list[str]
    summary_focus: str
    skills_to_feature: list[str]


class Stage2Verification(BaseModel):
    """Stage 2 self-verification block from LLM."""

    ats_keyword_score: int = Field(ge=1, le=10)
    keywords_added_in_review: list[str] = Field(default_factory=list)
    summary_rewritten: bool = False
    fact_verification_passed: bool = False
    hallucination_flags: list[str] = Field(default_factory=list)


class Stage2Output(BaseModel):
    """Stage 2: CV generation output (LLM Haiku call)."""

    verification: Stage2Verification
    cv_sections: CVSections


class Stage3Result(BaseModel):
    """Stage 3: Fact verification result (Python, no LLM call)."""

    cv_sections: CVSections
    fact_verification_passed: bool
    items_corrected: list[str] = Field(default_factory=list)
    items_removed: list[str] = Field(default_factory=list)
    ats_keyword_score: int = Field(default=0, ge=0, le=100)


# P2/P3: Ground Truth Input Models


class ParsedFacts(BaseModel):
    """Parsed CV facts for pipeline input — mirrors UserCV structure."""

    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    work_experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    summary_original: str | None = None


class GapAnalysisResponses(BaseModel):
    """Gap analysis responses for pipeline."""

    responses: list[dict[str, Any]] = Field(default_factory=list)


class CompanyContext(BaseModel):
    """Company context for Stage 2 CV generation."""

    company_name: str
    company_culture: str = ''
    products_services: list[str] = Field(default_factory=list)


class TailoredCVResponse(BaseModel):
    """Container for tailoring results and optional response metadata.

    P1 spec: Returns cv_sections structured object instead of tailored_cv text blob.
    """

    # Response wrapper fields
    success: bool | None = None
    error_message: str | None = None
    error_code: str | None = None
    download_url: str | None = None
    metadata: dict[str, Any] | None = None

    # P1: Structured CV sections (replaces TailoredCV.tailored_cv text blob per AC-P1-05)
    cv_sections: CVSections | None = None

    # P1: ATS scoring (0-100 integer, replaces estimated_ats_score which was 0-10)
    ats_score: int = Field(default=0, ge=0, le=100)
    ats_issues: list[ATSIssue] = Field(default_factory=list)
    keyword_match_score: int = Field(default=5, ge=1, le=10)
    keywords_missing: list[str] = Field(default_factory=list)
    fact_verification_passed: bool = False
    language: str = 'en'

    # Legacy fields (for backward compatibility)
    changes_made: list[ChangeLog] = Field(default_factory=list)
    relevance_scores: dict[str, float] = Field(default_factory=dict)
    average_relevance_score: float = 0.0
    keyword_matches: list[str] = Field(default_factory=list)
    # Keep estimated_ats_score as alias for ats_score during transition
    estimated_ats_score: int = Field(default=0, ge=0, le=100)

    @model_validator(mode='after')
    def _validate_consistency(self) -> 'TailoredCVResponse':
        if self.success is True:
            if self.cv_sections is None and self.metadata is None:
                raise ValueError('cv_sections or metadata is required when success is True')
        if self.success is False:
            if not self.error_message:
                raise ValueError('error_message is required when success is False')
        return self
