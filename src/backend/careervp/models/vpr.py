"""
Pydantic models for Value Proposition Report (VPR) generation.
Per docs/specs/03-vpr-generator.md and docs/features/CareerVP Prompt Library.md.

VPR is the strategic foundation document generated using Sonnet 4.5
that provides alignment mapping between CV facts and job requirements.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from careervp.models.job import CompanyContext, GapResponse, JobPosting


class EvidenceItem(BaseModel):
    """
    Single item in the Evidence & Alignment Matrix.
    Maps a job requirement to CV evidence with alignment scoring.
    """

    requirement: Annotated[str, Field(description='Job requirement being addressed')]
    evidence: Annotated[str, Field(description='CV fact or gap response supporting this requirement')]
    alignment_score: Annotated[
        Literal['STRONG', 'MODERATE', 'DEVELOPING'],
        Field(description='How well the evidence matches the requirement'),
    ]
    impact_potential: Annotated[str, Field(description='How this experience translates to role success')]


class GapStrategy(BaseModel):
    """
    Mitigation strategy for a gap in requirements.
    Per VPR structure: Gap Mitigation Strategies section.
    """

    gap: Annotated[str, Field(description='The missing or weak requirement')]
    mitigation_approach: Annotated[str, Field(description='Suggested talking points or reframing approach')]
    transferable_skills: Annotated[list[str], Field(default_factory=list, description='Related skills that partially address the gap')]


class TokenUsage(BaseModel):
    """
    LLM token usage and cost tracking.
    Per docs/features/CareerVP Prompt Library.md - Cost Tracking.
    """

    input_tokens: Annotated[int, Field(description='Number of input tokens')]
    output_tokens: Annotated[int, Field(description='Number of output tokens')]
    cost_usd: Annotated[float, Field(description='Total cost in USD')]
    model: Annotated[str, Field(description='Model ID used')]


class VPR(BaseModel):
    """
    Complete Value Proposition Report structure.
    Per docs/specs/03-vpr-generator.md Output Schema.
    """

    # Identification
    application_id: Annotated[str, Field(description='Unique application identifier')]
    user_id: Annotated[str, Field(description='User who owns this VPR')]

    # VPR Content Sections
    executive_summary: Annotated[str, Field(description='200-250 word summary of unique value proposition')]
    evidence_matrix: Annotated[
        list[EvidenceItem],
        Field(default_factory=list, description='Evidence & Alignment Matrix items'),
    ]
    differentiators: Annotated[
        list[str],
        Field(default_factory=list, description='3-5 strategic differentiators'),
    ]
    gap_strategies: Annotated[
        list[GapStrategy],
        Field(default_factory=list, description='Gap mitigation strategies'),
    ]
    cultural_fit: Annotated[str | None, Field(description='Cultural fit analysis based on company research')] = None
    talking_points: Annotated[
        list[str],
        Field(default_factory=list, description='5-7 recommended talking points for interviews'),
    ]
    keywords: Annotated[
        list[str],
        Field(default_factory=list, description='ATS-optimized keywords for CV tailoring'),
    ]

    # Metadata
    version: Annotated[int, Field(default=1, description='VPR version number')]
    language: Annotated[Literal['en', 'he'], Field(default='en', description='Language of VPR content')]
    created_at: Annotated[datetime, Field(default_factory=datetime.utcnow)]
    word_count: Annotated[int, Field(default=0, description='Total word count of VPR')]


class VPRRequest(BaseModel):
    """
    Request model for VPR generation endpoint.
    Per docs/specs/03-vpr-generator.md API Contract.
    """

    application_id: Annotated[str, Field(description='Unique application identifier')]
    user_id: Annotated[str, Field(description='User requesting VPR')]
    job_posting: Annotated[JobPosting, Field(description='Structured job posting data')]
    gap_responses: Annotated[
        list[GapResponse],
        Field(default_factory=list, description='Optional gap analysis responses'),
    ]
    company_context: Annotated[CompanyContext | None, Field(description='Optional company research data')] = None


class VPRResponse(BaseModel):
    """
    Response model for VPR generation endpoint.
    Per docs/specs/03-vpr-generator.md API Contract.
    """

    success: Annotated[bool, Field(description='Whether VPR generation succeeded')]
    vpr: Annotated[VPR | None, Field(description='Generated VPR if successful')] = None
    token_usage: Annotated[TokenUsage | None, Field(description='LLM token usage and cost')] = None
    generation_time_ms: Annotated[int, Field(default=0, description='Time taken to generate VPR in milliseconds')]
    error: Annotated[str | None, Field(description='Error message if failed')] = None
