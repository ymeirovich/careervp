"""
Pydantic models for the Company Research workflow.
Per docs/specs/02-company-research.md and Task 8.1 instructions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class ResearchSource(str, Enum):
    """Source used to collect company research content."""

    WEBSITE_SCRAPE = 'website_scrape'
    WEB_SEARCH = 'web_search'
    LLM_FALLBACK = 'llm_fallback'


class CompanyResearchRequest(BaseModel):
    """Input payload describing the company that requires research."""

    company_name: Annotated[str, Field(description='Name of the company to research')]
    domain: Annotated[str | None, Field(default=None, description='Company domain, e.g., example.com')] = None
    job_posting_url: Annotated[HttpUrl | None, Field(default=None, description='URL of the job posting to analyze')] = None
    job_posting_text: Annotated[str | None, Field(default=None, description='Job description text for LLM fallback')] = None


class CompanyResearchResult(BaseModel):
    """Structured research data fed into downstream personalization flows."""

    company_name: Annotated[str, Field(description='Company name associated with the research output')]
    overview: Annotated[str, Field(description='100-200 word narrative summary of the company')]
    values: Annotated[list[str], Field(default_factory=list, description='List of 3-5 core company values')]
    mission: Annotated[str | None, Field(default=None, description='Company mission statement if available')] = None
    strategic_priorities: Annotated[list[str], Field(default_factory=list, description='Current strategic priorities or initiatives')]
    recent_news: Annotated[list[str], Field(default_factory=list, description='Recent news items or announcements (last 6 months)')]
    financial_summary: Annotated[str | None, Field(default=None, description='Financial performance highlights if the company is public')] = None
    source: Annotated[ResearchSource, Field(default=ResearchSource.WEBSITE_SCRAPE, description='Primary source for the research content')] = (
        ResearchSource.WEBSITE_SCRAPE
    )
    source_urls: Annotated[list[str], Field(default_factory=list, description='Supporting URLs used for the research')]
    confidence_score: Annotated[float, Field(default=0.0, ge=0.0, le=1.0, description='Confidence score between 0.0 and 1.0')] = 0.0
    research_timestamp: Annotated[
        datetime, Field(default_factory=lambda: datetime.now(timezone.utc), description='UTC timestamp for when research completed')
    ]


class SearchResult(BaseModel):
    """Single search result entry returned by the web search fallback."""

    title: Annotated[str, Field(description='Headline/title of the search result')]
    url: Annotated[HttpUrl, Field(description='URL to the search result page')]
    snippet: Annotated[str, Field(description='Short snippet or summary provided by the search engine')]
