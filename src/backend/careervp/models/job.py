"""
Pydantic models for job posting data.
Per docs/specs/03-vpr-generator.md and docs/features/Job Post Example files.

Job postings are used as input for VPR generation and CV tailoring.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl


class JobPosting(BaseModel):
    """
    Structured job posting data extracted from user input.
    Based on docs/features/Job Post Example 1.md and Job Post Example 2.md.
    """

    company_name: Annotated[str, Field(description='Company name')]
    role_title: Annotated[str, Field(description='Job title/position')]
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
    mission: Annotated[str | None, Field(description='Company mission statement')] = None
    values: Annotated[list[str], Field(default_factory=list, description='Core company values')]
    strategic_priorities: Annotated[list[str], Field(default_factory=list, description='Current strategic priorities')]
    recent_news: Annotated[list[str], Field(default_factory=list, description='Recent news/developments')]
    industry: Annotated[str | None, Field(description='Industry/sector')] = None
