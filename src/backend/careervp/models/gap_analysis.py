"""Pydantic models for gap analysis request/response."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from careervp.models.job import JobPosting


class GapAnalysisRequest(BaseModel):
    """Request for gap analysis generation."""

    user_id: Annotated[str, Field(min_length=1)]
    cv_id: Annotated[str, Field(min_length=1)]
    job_posting: JobPosting
    language: Annotated[Literal["en", "he"], Field(default="en")]


class GapQuestion(BaseModel):
    """Single gap analysis question."""

    question_id: Annotated[str, Field(min_length=1)]
    question: Annotated[str, Field(min_length=1)]
    impact: Annotated[Literal["HIGH", "MEDIUM", "LOW"], Field(description="Impact level")]
    probability: Annotated[Literal["HIGH", "MEDIUM", "LOW"], Field(description="Probability level")]
    gap_score: Annotated[float, Field(ge=0.0, le=1.0)]


class GapAnalysisResponse(BaseModel):
    """Response containing generated questions and metadata."""

    questions: list[GapQuestion]
    metadata: dict[str, Any]
