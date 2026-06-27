"""
Pydantic models for job posting data.
Per docs/specs/03-vpr-generator.md and docs/features/Job Post Example files.

Job postings are used as input for VPR generation and CV tailoring.
"""

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, Field, HttpUrl


class Job(BaseModel):
    """Canonical job posting model for API `/jobs` endpoints."""

    job_id: Annotated[str, Field(description='Unique job identifier')]
    user_id: Annotated[str, Field(description='Owning user identifier')]
    title: Annotated[str, Field(description='Job title')]
    company: Annotated[str, Field(description='Company name')]
    description: Annotated[str, Field(description='Job description')]
    status: Annotated[str, Field(default='active', description='Job status')]
    created_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(timezone.utc))]
    url: Annotated[str | None, Field(default=None, description='Optional source URL')] = None
    requirements: Annotated[list[str], Field(default_factory=list, description='Optional extracted requirements')]

    def to_api_dict(self) -> dict[str, object]:
        """Serialize in OpenAPI-compatible response shape."""
        return {
            'id': self.job_id,
            'job_id': self.job_id,
            'user_id': self.user_id,
            'title': self.title,
            'company_name': self.company,
            'description': self.description,
            'status': self.status,
            'url': self.url,
            'requirements': self.requirements,
            'created_at': self.created_at.isoformat(),
        }


class JobPosting(BaseModel):
    """
    Structured job posting data extracted from user input.
    Based on docs/features/Job Post Example 1.md and Job Post Example 2.md.
    """

    company_name: Annotated[
        str,
        Field(
            description='Company name',
            validation_alias=AliasChoices('company_name', 'company', 'employer'),
        ),
    ]
    role_title: Annotated[
        str,
        Field(
            description='Job title/position',
            validation_alias=AliasChoices('role_title', 'title', 'job_title', 'position'),
        ),
    ]
    description: Annotated[str | None, Field(description='About the role/company')] = None
    responsibilities: Annotated[list[str], Field(default_factory=list, description='Job responsibilities/duties')]
    requirements: Annotated[list[str], Field(default_factory=list, description='Required qualifications')]
    nice_to_have: Annotated[list[str], Field(default_factory=list, description='Preferred/optional qualifications')]
    language: Annotated[Literal['en', 'he'], Field(default='en', description='Detected language of posting')]
    source_url: Annotated[HttpUrl | None, Field(description='URL of original job posting')] = None


class GapResponse(BaseModel):
    """
    User response to a gap analysis question.
    Per docs/features/CareerVP Prompt Library.md - Gap Analysis section.
    """

    question_id: Annotated[str, Field(description='Unique question identifier')]
    question: Annotated[str, Field(description='The gap analysis question')]
    answer: Annotated[str, Field(description='User-provided answer')]
    destination: Annotated[
        Literal['CV_IMPACT', 'INTERVIEW_MVP_ONLY'],
        Field(default='CV_IMPACT', description='Where this response will be used'),
    ]


class CompanyContext(BaseModel):
    """
    Company research data for VPR generation.
    Per docs/specs/02-company-research.md.
    """

    company_name: Annotated[str, Field(description='Company name')]
    overview: Annotated[str | None, Field(description='Company overview')] = None
    mission: Annotated[str | None, Field(description='Company mission statement')] = None
    values: Annotated[list[str], Field(default_factory=list, description='Core company values')]
    strategic_priorities: Annotated[list[str], Field(default_factory=list, description='Current strategic priorities')]
    recent_news: Annotated[list[str], Field(default_factory=list, description='Recent news/developments')]
    financial_summary: Annotated[str | None, Field(description='Financial performance highlights')] = None
    key_products: Annotated[list[str], Field(default_factory=list, description='Key products, services, or business lines')]
    company_size: Annotated[str | None, Field(description='Company size or employee range')] = None
    key_executives: Annotated[list[str], Field(default_factory=list, description='Named executives or senior leaders')]
    competitive_positioning: Annotated[str | None, Field(description='Market positioning')] = None
    growth_signals: Annotated[list[str], Field(default_factory=list, description='Signals of company growth')]
    industry: Annotated[str | None, Field(description='Industry/sector')] = None
