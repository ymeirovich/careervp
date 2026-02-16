"""Pydantic models for Interview Preparation."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class InterviewAnswer(BaseModel):
    """STAR-method structured answer."""

    situation: Annotated[str, Field(default='', description='Context/situation')]
    task: Annotated[str, Field(default='', description='Task/challenge')]
    action: Annotated[str, Field(default='', description='Actions taken')]
    result: Annotated[str, Field(default='', description='Outcomes/results')]
    full_text: Annotated[str, Field(default='', description='Complete answer text')]
    word_count: Annotated[int, Field(default=0)]


class InterviewQuestion(BaseModel):
    """Single interview preparation question with suggested answer."""

    question_id: Annotated[str, Field(description='Unique question ID')]
    question: Annotated[str, Field(description='Interview question text')]
    question_type: Annotated[
        Literal['behavioral', 'technical', 'situational', 'gap_focused'],
        Field(description='Question category'),
    ]
    difficulty: Annotated[Literal['easy', 'medium', 'hard'], Field(default='medium')]
    suggested_answer: Annotated[InterviewAnswer | None, Field(default=None)]
    why_asked: Annotated[str, Field(default='', description='Why interviewer asks this')]
    tips: Annotated[list[str], Field(default_factory=list)]


class InterviewerQuestion(BaseModel):
    """Question candidate should ask the interviewer."""

    question: Annotated[str, Field(description='Question text')]
    purpose: Annotated[str, Field(default='', description='Why to ask this')]


class InterviewPrep(BaseModel):
    """Complete interview preparation package."""

    prep_id: Annotated[str, Field(description='Unique prep ID')]
    user_id: Annotated[str, Field(description='User ID')]
    job_id: Annotated[str | None, Field(default=None)]
    vpr_id: Annotated[str, Field(description='Source VPR ID')]
    questions: Annotated[list[InterviewQuestion], Field(default_factory=list)]
    questions_to_ask: Annotated[list[InterviewerQuestion], Field(default_factory=list)]
    salary_guidance: Annotated[str | None, Field(default=None)]
    pre_interview_checklist: Annotated[list[str], Field(default_factory=list)]
    created_at: Annotated[datetime, Field(default_factory=datetime.utcnow)]
    version: Annotated[int, Field(default=1)]


class InterviewPrepRequest(BaseModel):
    """Request for interview prep generation."""

    user_id: Annotated[str, Field(min_length=1)]
    vpr_id: Annotated[str, Field(min_length=1)]
    job_id: Annotated[str | None, Field(default=None)]
    gap_response_ids: Annotated[list[str], Field(default_factory=list)]
    focus_areas: Annotated[list[str], Field(default_factory=list)]
    question_count: Annotated[int, Field(default=5, ge=1, le=10)]


class InterviewPrepResponse(BaseModel):
    """Response from interview prep generation."""

    success: Annotated[bool, Field(description='Whether generation succeeded')]
    interview_prep: Annotated[InterviewPrep | None, Field(default=None)]
    generation_time_ms: Annotated[int, Field(default=0)]
    error: Annotated[str | None, Field(default=None)]
