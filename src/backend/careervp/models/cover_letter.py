"""Pydantic models for Cover Letter generation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class CoverLetterOptions(BaseModel):
    """Options for cover letter generation."""

    tone: Annotated[
        Literal['professional', 'conversational', 'formal'],
        Field(default='professional'),
    ]
    length: Annotated[
        Literal['short', 'standard', 'long'],
        Field(default='standard'),
    ]
    include_portfolio_link: Annotated[bool, Field(default=False)]


class CoverLetterParagraph(BaseModel):
    """Single paragraph of a cover letter."""

    type: Annotated[
        Literal['hook', 'proof_points', 'close'],
        Field(description='Paragraph type'),
    ]
    content: Annotated[str, Field(description='Paragraph text')]
    word_count: Annotated[int, Field(default=0)]


class CoverLetter(BaseModel):
    """Complete cover letter output."""

    cover_letter_id: Annotated[str, Field(description='Unique cover letter identifier')]
    user_id: Annotated[str, Field(description='User who owns this')]
    job_id: Annotated[str, Field(description='Associated job')]
    cv_id: Annotated[str, Field(description='Source CV')]
    vpr_id: Annotated[str, Field(description='Source VPR')]
    full_text: Annotated[str, Field(description='Complete cover letter text')]
    paragraphs: Annotated[
        list[CoverLetterParagraph],
        Field(default_factory=list),
    ]
    word_count: Annotated[int, Field(default=0)]
    tone: Annotated[str, Field(default='professional')]
    created_at: Annotated[datetime, Field(default_factory=datetime.utcnow)]
    version: Annotated[int, Field(default=1)]


class CoverLetterRequest(BaseModel):
    """Request model for cover letter generation."""

    user_id: Annotated[str, Field(min_length=1)]
    cv_id: Annotated[str, Field(min_length=1)]
    job_id: Annotated[str, Field(min_length=1)]
    vpr_id: Annotated[str, Field(min_length=1)]
    company_name: Annotated[str, Field(min_length=1)]
    job_title: Annotated[str, Field(min_length=1)]
    job_description: Annotated[str, Field(min_length=1)]
    gap_response_ids: Annotated[list[str], Field(default_factory=list)]
    company_research_id: Annotated[str | None, Field(default=None)] = None
    options: Annotated[CoverLetterOptions | None, Field(default=None)] = None


class CoverLetterResponse(BaseModel):
    """Response model for cover letter generation."""

    success: Annotated[bool, Field(description='Whether generation succeeded')]
    cover_letter: Annotated[CoverLetter | None, Field(default=None)] = None
    generation_time_ms: Annotated[int, Field(default=0)]
    error: Annotated[str | None, Field(description='Error message if failed')] = None
