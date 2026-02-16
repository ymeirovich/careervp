"""Interview preparation generation logic."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from careervp.logic.llm_client import LLMClient
from careervp.logic.prompts.interview_prep_prompt import build_system_prompt, build_user_prompt
from careervp.models.interview_prep import (
    InterviewAnswer,
    InterviewerQuestion,
    InterviewPrep,
    InterviewPrepRequest,
    InterviewPrepResponse,
    InterviewQuestion,
)
from careervp.models.result import Result, ResultCode

MAX_QUESTIONS = 10
MAX_PER_TYPE = 4
ANSWER_MIN_WORDS = 150
ANSWER_MAX_WORDS = 300


async def _maybe_await(value: Any) -> Any:
    if asyncio.iscoroutine(value):
        return await value
    return value


async def generate_interview_prep(
    request: InterviewPrepRequest,
    vpr_data: dict[str, Any],
    gap_responses: list[dict[str, Any]] | None = None,
    job_title: str = '',
    company_name: str = '',
) -> Result[InterviewPrepResponse]:
    """Generate personalized interview preparation."""
    start_time = time.perf_counter()

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        vpr_data=vpr_data,
        gap_responses=gap_responses,
        job_title=job_title,
        company_name=company_name,
        focus_areas=request.focus_areas,
        question_count=request.question_count,
    )

    llm_client = LLMClient()
    try:
        llm_result = await _maybe_await(llm_client.generate(prompt=f'{system_prompt}\n\n{user_prompt}'))
    except TimeoutError as exc:
        return Result(success=False, error=str(exc), code=ResultCode.TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        return Result(
            success=False,
            error=f'LLM invocation failed: {exc}',
            code=ResultCode.LLM_API_ERROR,
        )

    # Extract raw text from LLM response
    if isinstance(llm_result, Result):
        if not llm_result.success:
            return Result(success=False, error=llm_result.error or 'LLM failed', code=ResultCode.LLM_API_ERROR)
        raw = llm_result.data if isinstance(llm_result.data, str) else json.dumps(llm_result.data)
    elif isinstance(llm_result, dict):
        raw = llm_result.get('text', json.dumps(llm_result))
    elif isinstance(llm_result, str):
        raw = llm_result
    else:
        raw = str(llm_result)

    try:
        prep = _parse_interview_prep(raw, request)
    except ValueError as exc:
        return Result(success=False, error=f'Parse failed: {exc}', code=ResultCode.INTERNAL_ERROR)

    generation_time_ms = int((time.perf_counter() - start_time) * 1000)

    response = InterviewPrepResponse(
        success=True,
        interview_prep=prep,
        generation_time_ms=generation_time_ms,
        error=None,
    )

    return Result(success=True, data=response, code=ResultCode.INTERVIEW_QUESTIONS_GENERATED)


def _strip_code_blocks(text: str) -> str:
    """Remove markdown code block markers from LLM output."""
    cleaned = text.strip()
    if cleaned.startswith('```'):
        first_nl = cleaned.find('\n')
        if first_nl != -1:
            cleaned = cleaned[first_nl + 1 :]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return cleaned


def _parse_answer(answer_data: dict[str, Any]) -> InterviewAnswer:
    """Parse a single STAR-method answer from raw dict."""
    full_text = answer_data.get('full_text', '')
    if not full_text:
        parts = [
            answer_data.get('situation', ''),
            answer_data.get('task', ''),
            answer_data.get('action', ''),
            answer_data.get('result', ''),
        ]
        full_text = ' '.join(p for p in parts if p)
    return InterviewAnswer(
        situation=answer_data.get('situation', ''),
        task=answer_data.get('task', ''),
        action=answer_data.get('action', ''),
        result=answer_data.get('result', ''),
        full_text=full_text,
        word_count=len(full_text.split()),
    )


VALID_QUESTION_TYPES = frozenset(('behavioral', 'technical', 'situational', 'gap_focused'))


def _parse_questions(raw_questions: list[dict[str, Any]]) -> list[InterviewQuestion]:
    """Parse and filter interview questions from payload."""
    questions: list[InterviewQuestion] = []
    type_counts: dict[str, int] = {}

    for raw_q in raw_questions:
        q_type = raw_q.get('question_type', 'behavioral')
        if q_type not in VALID_QUESTION_TYPES:
            q_type = 'behavioral'

        type_counts[q_type] = type_counts.get(q_type, 0) + 1
        if type_counts[q_type] > MAX_PER_TYPE:
            continue
        if len(questions) >= MAX_QUESTIONS:
            break

        answer_data = raw_q.get('suggested_answer')
        suggested_answer = _parse_answer(answer_data) if answer_data and isinstance(answer_data, dict) else None

        questions.append(
            InterviewQuestion(
                question_id=raw_q.get('question_id', f'q{len(questions) + 1}'),
                question=raw_q.get('question', ''),
                question_type=q_type,
                difficulty=raw_q.get('difficulty', 'medium'),
                suggested_answer=suggested_answer,
                why_asked=raw_q.get('why_asked', ''),
                tips=raw_q.get('tips', []),
            )
        )

    return questions


def _parse_interview_prep(raw_text: str, request: InterviewPrepRequest) -> InterviewPrep:
    """Parse LLM JSON output into InterviewPrep model."""
    cleaned = _strip_code_blocks(raw_text)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f'Invalid JSON: {exc}') from exc

    questions = _parse_questions(payload.get('questions', []))

    questions_to_ask: list[InterviewerQuestion] = [
        InterviewerQuestion(question=raw_qa.get('question', ''), purpose=raw_qa.get('purpose', ''))
        for raw_qa in payload.get('questions_to_ask', [])
        if isinstance(raw_qa, dict)
    ]

    return InterviewPrep(
        prep_id=str(uuid.uuid4()),
        user_id=request.user_id,
        job_id=request.job_id,
        vpr_id=request.vpr_id,
        questions=questions,
        questions_to_ask=questions_to_ask,
        salary_guidance=payload.get('salary_guidance'),
        pre_interview_checklist=payload.get('pre_interview_checklist', []),
        created_at=datetime.now(timezone.utc),
        version=1,
    )
