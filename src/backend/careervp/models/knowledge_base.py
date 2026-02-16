"""Pydantic models for Knowledge Base storage."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field


class KnowledgeEntry(BaseModel):
    """Base knowledge base entry."""

    user_id: Annotated[str, Field(min_length=1)]
    entity_type: Annotated[str, Field(description='Type of knowledge entry')]
    created_at: Annotated[datetime, Field(default_factory=datetime.utcnow)]
    ttl: Annotated[int | None, Field(default=None, description='TTL in seconds')]


class GapResponseEntry(KnowledgeEntry):
    """Stored gap analysis response."""

    entity_type: str = 'GAP_RESPONSE'
    job_id: Annotated[str, Field(min_length=1)]
    cv_id: Annotated[str, Field(min_length=1)]
    question_id: Annotated[str, Field(min_length=1)]
    response_id: Annotated[str, Field(min_length=1)]
    response_text: Annotated[str, Field(min_length=1)]


class CompanyResearchEntry(KnowledgeEntry):
    """Cached company research data."""

    entity_type: str = 'COMPANY_RESEARCH'
    job_id: Annotated[str, Field(min_length=1)]
    company_research_id: Annotated[str, Field(min_length=1)]
    company_name: Annotated[str, Field(min_length=1)]
    research_data: Annotated[dict[str, Any], Field(default_factory=dict)]
    cached_at: Annotated[datetime, Field(default_factory=datetime.utcnow)]


class KnowledgeBaseRequest(BaseModel):
    """Request to query knowledge base."""

    user_id: Annotated[str, Field(min_length=1)]
    job_id: Annotated[str | None, Field(default=None)]
    entity_type: Annotated[str | None, Field(default=None)]


class KnowledgeBaseResponse(BaseModel):
    """Response from knowledge base query."""

    success: Annotated[bool, Field(default=True)]
    entries: Annotated[list[dict[str, Any]], Field(default_factory=list)]
    count: Annotated[int, Field(default=0)]
    error: Annotated[str | None, Field(default=None)]
