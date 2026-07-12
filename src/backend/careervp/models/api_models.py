"""Canonical OpenAPI request/response models for CareerVP API v1."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, EmailStr, Field, field_validator

ArtifactStatus = Literal['pending', 'processing', 'completed', 'failed', 'cancelled', 'expired', 'not_generated', 'edited']


class APIModel(BaseModel):
    """Shared base for strict API schema validation and (de)serialization."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True, str_strip_whitespace=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'APIModel':
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, payload: str) -> 'APIModel':
        return cls.model_validate_json(payload)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode='json', by_alias=True, exclude_none=True)

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, exclude_none=True)


# ==========================================================================
# AUTH SCHEMAS
# ==========================================================================


class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)

    @field_validator('password', 'name')
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('must not be empty')
        return value


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator('password')
    @classmethod
    def _password_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('must not be empty')
        return value


class AuthResponse(APIModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str = 'Bearer'


# ==========================================================================
# USER SCHEMAS
# ==========================================================================


class UserProfile(APIModel):
    id: str | None = None
    email: EmailStr | None = None
    name: str | None = None
    created_at: datetime | None = None


class UpdateUserRequest(APIModel):
    name: str | None = None
    timezone: str | None = None


class CVUploadRequest(APIModel):
    cv_content: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    file_type: Literal['pdf', 'docx', 'txt'] | None = None


class CVUploadResponse(APIModel):
    cv_id: str | None = None
    status: Literal['processing', 'parsed', 'failed'] | None = None
    parsed_data: dict[str, Any] | None = None


class CVListItem(APIModel):
    id: str | None = None
    file_name: str | None = None
    uploaded_at: datetime | None = None


class CVListResponse(APIModel):
    cvs: list[CVListItem] = Field(default_factory=list)
    cursor: str | None = None


# ==========================================================================
# JOB SCHEMAS
# ==========================================================================


class JobCreateRequest(APIModel):
    title: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    url: str | None = None
    requirements: list[str] = Field(default_factory=list)


class JobResponse(APIModel):
    id: str | None = None
    title: str | None = None
    company_name: str | None = None
    description: str | None = None
    url: str | None = None
    requirements: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class JobListResponse(APIModel):
    jobs: list[JobResponse] = Field(default_factory=list)


class ContractJobDetail(APIModel):
    job_id: str
    user_id: str
    title: str
    company_name: str
    description: str | None = None
    status: str
    created_at: datetime | None = None
    url: str | None = None
    requirements: list[str] = Field(default_factory=list)


class HubArtifact(APIModel):
    status: ArtifactStatus
    artifact_id: str | None


class ApplicationHubApplication(APIModel):
    application_id: str
    state: str
    created_at: datetime
    trial_credit_consumed: bool


class ApplicationHubCV(APIModel):
    cv_id: str


class ApplicationHubGapAnalysis(APIModel):
    questions: list[dict[str, Any]] = Field(default_factory=list)
    responses: list[dict[str, Any]] = Field(default_factory=list)


class ApplicationHubArtifacts(APIModel):
    vpr: HubArtifact
    cover_letter: HubArtifact
    interview_prep: HubArtifact
    cv_tailored: HubArtifact
    gap_analysis: HubArtifact


class ApplicationHubData(APIModel):
    application: ApplicationHubApplication
    job: ContractJobDetail
    cv: ApplicationHubCV | None = None
    gap_analysis: ApplicationHubGapAnalysis
    artifacts: ApplicationHubArtifacts
    reload_route: str | None = None


# ==========================================================================
# VPR SCHEMAS
# ==========================================================================


class VPRGenerateOptions(APIModel):
    include_company_research: bool = True
    tone: Literal['professional', 'conversational', 'formal'] | None = None


class VPRGenerateRequest(APIModel):
    cv_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    application_id: str | None = None
    gap_response_ids: list[str] = Field(default_factory=list)
    options: VPRGenerateOptions | None = None
    # When True, an explicit regeneration is requested: bypass the idempotency
    # short-circuit for an already-completed job and create a fresh job.
    force: bool = False


class AsyncTaskResponse(APIModel):
    request_id: str | None = None
    job_id: str | None = None
    status: Literal['processing', 'completed']
    estimated_time_seconds: int | None = None


class VPRGenerateResponse(APIModel):
    request_id: str | None = None
    status: Literal['processing'] | None = None
    estimated_time_seconds: int | None = None
    webhook_url: str | None = None


class VPRDifferentiator(APIModel):
    text: str | None = None
    source: Literal['cv', 'gap_response'] | None = None


class VPRMetaEvaluation(APIModel):
    persuasion_score: float | None = None
    completeness_score: float | None = None


class VPRStatusResult(APIModel):
    uvp: str | None = None
    differentiators: list[VPRDifferentiator] = Field(default_factory=list)
    strategic_narrative: str | None = None
    company_job_fit_score: float | None = None
    meta_evaluation: VPRMetaEvaluation | None = None
    download_url: str | None = None


class VPRStatusResponse(APIModel):
    id: str | None = None
    status: ArtifactStatus
    result: VPRStatusResult | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class VPRListItem(APIModel):
    id: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    created_at: datetime | None = None


class VPRListResponse(APIModel):
    vprs: list[VPRListItem] = Field(default_factory=list)


# ==========================================================================
# GAP ANALYSIS SCHEMAS
# ==========================================================================


class GapQuestionRequest(APIModel):
    cv_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    max_questions: int = 10
    focus_areas: list[str] = Field(default_factory=list)


class GapQuestionItem(APIModel):
    id: str | None = None
    text: str | None = None
    tags: list[str] = Field(default_factory=list)
    strategic_intent: str | None = None
    evidence_gap: str | None = None


class MissingQualification(APIModel):
    skill: str | None = None
    priority: str | None = None


class GapQuestionResponse(APIModel):
    questions: list[GapQuestionItem] = Field(default_factory=list)
    missing_qualifications: list[MissingQualification] = Field(default_factory=list)


class GapResponseQuantifiableData(APIModel):
    team_size: int | None = None
    duration_months: int | None = None
    percentage: float | None = None


class GapResponseItem(APIModel):
    question_id: str = Field(min_length=1)
    response: str = Field(min_length=1)
    quantifiable_data: GapResponseQuantifiableData | None = None


class GapResponseRequest(APIModel):
    responses: list[GapResponseItem]

    @field_validator('responses')
    @classmethod
    def _responses_required(cls, value: list[GapResponseItem]) -> list[GapResponseItem]:
        if not value:
            raise ValueError('responses must not be empty')
        return value


class GapImpactStatement(APIModel):
    text: str | None = None
    evidence_type: Literal['CV_IMPACT', 'INTERVIEW_PREP'] | None = None
    usable_in: list[str] = Field(default_factory=list)


class GapResponseResponse(APIModel):
    status: str | None = None
    impact_statements: list[GapImpactStatement] = Field(default_factory=list)


class GapQuestionHistoryResponse(APIModel):
    questions: list[Any] = Field(default_factory=list)


# ==========================================================================
# CV TAILORING SCHEMAS
# ==========================================================================


class CVTailoringOptions(APIModel):
    preserve_length: bool = True
    highlight_keywords: bool = True
    target_ats: str = 'standard'


class CVTailoringRequest(APIModel):
    cv_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    vpr_id: str | None
    options: CVTailoringOptions | None = None


class CVTailoringResponse(APIModel):
    request_id: str | None = None
    status: Literal['processing'] | None = None
    estimated_time_seconds: int | None = None


class KeywordMatches(APIModel):
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class FVSValidation(APIModel):
    is_valid: bool | None = None
    violations: list[str] = Field(default_factory=list)


class CVTailoringStatusResult(APIModel):
    tailored_cv: str | None = None
    ats_score: float | None = None
    ats_grade: str | None = None
    ats_result: dict[str, Any] | None = None
    cv_sections: dict[str, Any] | None = None
    keyword_match_score: float | None = None
    keywords_matched: list[str] = Field(default_factory=list)
    keywords_missing: list[str] = Field(default_factory=list)
    fact_verification_detail: dict[str, Any] | None = None
    keyword_matches: KeywordMatches | None = None
    suggestions: list[str] = Field(default_factory=list)
    fvs_validation: FVSValidation | None = None


class CVTailoringStatusResponse(APIModel):
    id: str | None = None
    status: ArtifactStatus
    version: int | None = None
    language: str | None = None
    generated_at: datetime | None = None
    updated_at: datetime | None = None
    result: CVTailoringStatusResult | None = None


class CVTailoringListResponse(APIModel):
    tailored_cvs: list[Any] = Field(default_factory=list)


# ==========================================================================
# COVER LETTER SCHEMAS
# ==========================================================================


class CoverLetterOptions(APIModel):
    tone: Literal['professional', 'conversational', 'formal'] | None = None
    length: Literal['short', 'standard', 'long'] | None = None
    include_portfolio_link: bool = False


class CoverLetterRequest(APIModel):
    cv_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    application_id: str | None = None
    vpr_id: str = Field(min_length=1)
    gap_response_ids: list[str]
    company_research_id: str | None = None
    options: CoverLetterOptions | None = None

    @field_validator('gap_response_ids')
    @classmethod
    def _gap_ids_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError('gap_response_ids must not be empty')
        return value


class CoverLetterResponse(APIModel):
    request_id: str | None = None
    status: Literal['processing'] | None = None
    estimated_time_seconds: int | None = None


# ==========================================================================
# AI-ASSIST SCHEMAS (FE-UI-046)
# ==========================================================================


class AIAssistRequest(APIModel):
    """Field-scoped AI-assist request.

    The client supplies ONLY these fields. The server resolves all other
    cross-artifact context from DynamoDB by (JWT user_id, application_id).
    """

    artifact_type: Literal['gap_analysis', 'cv_tailored', 'cover_letter', 'interview_prep']
    artifact_id: str = Field(min_length=1)
    application_id: str = Field(min_length=1)
    field_key: str = Field(min_length=1)
    current_text: str = ''
    locale: str = 'en'


class AIAssistResponse(APIModel):
    generated_markdown: str
    model: str
    tokens: int = 0


class CoverLetterHookParagraph(APIModel):
    word_count: int | None = None
    includes_uvp: bool | None = None
    includes_company_reference: bool | None = None


class CoverLetterProofPointsParagraph(APIModel):
    requirements_matched: int | None = None
    claims_verified: bool | None = None
    quantified_evidence: bool | None = None


class CoverLetterCloseParagraph(APIModel):
    word_count: int | None = None
    includes_cta: bool | None = None


class CoverLetterParagraphs(APIModel):
    hook: CoverLetterHookParagraph | None = None
    proof_points: CoverLetterProofPointsParagraph | None = None
    close: CoverLetterCloseParagraph | None = None


class CoverLetterStatusResult(APIModel):
    cover_letter: str | None = None
    paragraphs: CoverLetterParagraphs | None = None
    fvs_validation: FVSValidation | None = None


class CoverLetterStatusResponse(APIModel):
    id: str | None = None
    status: str
    updated_at: datetime | None = None
    version: int | None = None
    result: CoverLetterStatusResult | None = None
    error: str | None = None


class CoverLetterListResponse(APIModel):
    cover_letters: list[Any] = Field(default_factory=list)


# ==========================================================================
# INTERVIEW PREP SCHEMAS
# ==========================================================================


class InterviewPrepRequest(APIModel):
    vpr_id: str = Field(min_length=1)
    gap_response_ids: list[str]
    focus_areas: list[str] = Field(default_factory=list)
    question_count: int = 10
    # Optional context fields for agentic architecture alignment (section 3.7).
    # Backend resolves these server-side; clients that omit them continue to work.
    application_id: str | None = None
    job_id: str | None = None
    language: str = 'en'

    @field_validator('gap_response_ids')
    @classmethod
    def _gap_ids_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError('gap_response_ids must not be empty')
        return value


class InterviewPrepResponse(APIModel):
    request_id: str | None = None
    status: str | None = None


class InterviewSuggestedAnswer(APIModel):
    format: str | None = None
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    full_text: str | None = None


class InterviewPrepQuestion(APIModel):
    id: str | None = None
    text: str | None = None
    question_type: str | None = None
    answer: str | None = None
    answer_version: int | None = None
    answer_updated_at: datetime | None = None
    suggested_answer: InterviewSuggestedAnswer | None = None


class InterviewPrepStatusResult(APIModel):
    questions: list[InterviewPrepQuestion] = Field(default_factory=list)
    questions_to_ask: list[dict[str, str]] = Field(default_factory=list)
    pre_interview_checklist: list[str] = Field(default_factory=list)
    salary_guidance: str | None = None
    interview_report: dict[str, str] | None = None


class InterviewPrepStatusResponse(APIModel):
    id: str | None = None
    status: str
    updated_at: datetime | None = None
    version: int | None = None
    result: InterviewPrepStatusResult | None = None
    error: str | None = None


class InterviewPrepPatchResponse(APIModel):
    status: str
    interview_prep_id: str | None = None
    question_id: str
    answer: str
    answer_version: int | None = None
    answer_updated_at: datetime | None = None


# ==========================================================================
# COMPANY RESEARCH SCHEMAS
# ==========================================================================


class CompanyResearchRequest(APIModel):
    job_id: str = Field(min_length=1)
    url: AnyUrl | None = None
    company_name: str | None = None


class CompanyResearchResponse(APIModel):
    request_id: str | None = None
    status: str | None = None


class RecentNewsItem(APIModel):
    title: str | None = None
    date: str | None = None


class CompanyResearchResultResponse(APIModel):
    id: str
    company_name: str | None = None
    mission: str | None = None
    values: list[str] | None = None
    recent_news: list[RecentNewsItem | str] | None = None
    culture: str | None = None
    products: list[str] | None = None
    funding_status: str | None = None
    size_range: str | None = None
    industry: str | None = None


class ExportResponse(APIModel):
    download_url: str
    expires_at: datetime


# ==========================================================================
# ERROR + HEALTH SCHEMAS
# ==========================================================================


class ErrorDetail(APIModel):
    field: str | None = None
    message: str | None = None


class ErrorObject(APIModel):
    code: str | None = None
    message: str | None = None
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(APIModel):
    error: str | None = None
    message: str | None = None
    classification: str | None = None
    error_code: str | None = None
    field: str | None = None


class HealthServices(APIModel):
    dynamodb: str | None = None
    lambda_service: str | None = Field(default=None, alias='lambda')
    bedrock: str | None = None


class HealthResponse(APIModel):
    status: Literal['healthy', 'degraded', 'unhealthy']
    timestamp: datetime
    version: str
    services: HealthServices | None = None


__all__ = [
    'APIModel',
    'RegisterRequest',
    'LoginRequest',
    'AuthResponse',
    'UserProfile',
    'UpdateUserRequest',
    'CVUploadRequest',
    'CVUploadResponse',
    'CVListItem',
    'CVListResponse',
    'JobCreateRequest',
    'JobResponse',
    'JobListResponse',
    'ArtifactStatus',
    'ContractJobDetail',
    'HubArtifact',
    'ApplicationHubApplication',
    'ApplicationHubCV',
    'ApplicationHubGapAnalysis',
    'ApplicationHubArtifacts',
    'ApplicationHubData',
    'AsyncTaskResponse',
    'VPRGenerateOptions',
    'VPRGenerateRequest',
    'VPRGenerateResponse',
    'VPRDifferentiator',
    'VPRMetaEvaluation',
    'VPRStatusResult',
    'VPRStatusResponse',
    'VPRListItem',
    'VPRListResponse',
    'GapQuestionRequest',
    'GapQuestionItem',
    'MissingQualification',
    'GapQuestionResponse',
    'GapResponseQuantifiableData',
    'GapResponseItem',
    'GapResponseRequest',
    'GapImpactStatement',
    'GapResponseResponse',
    'GapQuestionHistoryResponse',
    'CVTailoringOptions',
    'CVTailoringRequest',
    'CVTailoringResponse',
    'KeywordMatches',
    'FVSValidation',
    'CVTailoringStatusResult',
    'CVTailoringStatusResponse',
    'CVTailoringListResponse',
    'CoverLetterOptions',
    'CoverLetterRequest',
    'CoverLetterResponse',
    'CoverLetterHookParagraph',
    'CoverLetterProofPointsParagraph',
    'CoverLetterCloseParagraph',
    'CoverLetterParagraphs',
    'CoverLetterStatusResult',
    'CoverLetterStatusResponse',
    'CoverLetterListResponse',
    'InterviewPrepRequest',
    'InterviewPrepResponse',
    'InterviewSuggestedAnswer',
    'InterviewPrepQuestion',
    'InterviewPrepStatusResult',
    'InterviewPrepStatusResponse',
    'InterviewPrepPatchResponse',
    'CompanyResearchRequest',
    'CompanyResearchResponse',
    'RecentNewsItem',
    'CompanyResearchResultResponse',
    'ExportResponse',
    'ErrorDetail',
    'ErrorObject',
    'ErrorResponse',
    'HealthServices',
    'HealthResponse',
]
