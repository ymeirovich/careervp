"""Gap analysis logic: generate and score gap questions."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from careervp.logic.llm_client import LLMClient
from careervp.logic.prompts.gap_analysis_prompt import (
    create_gap_analysis_system_prompt,
    create_gap_analysis_user_prompt,
)
from careervp.models.result import Result, ResultCode

IMPACT_SCORES = {'HIGH': 1.0, 'MEDIUM': 0.6, 'LOW': 0.3}
PROBABILITY_SCORES = {'HIGH': 1.0, 'MEDIUM': 0.6, 'LOW': 0.3}


def calculate_gap_score(impact: str, probability: str) -> float:
    """Calculate gap score with weighted impact/probability."""
    if impact not in IMPACT_SCORES:
        raise ValueError('Invalid impact level')
    if probability not in PROBABILITY_SCORES:
        raise ValueError('Invalid probability level')
    score = (0.7 * IMPACT_SCORES[impact]) + (0.3 * PROBABILITY_SCORES[probability])
    return round(score, 2)


async def _maybe_await(value: Any) -> Any:
    if asyncio.iscoroutine(value):
        return await value
    return value


async def generate_gap_questions(
    user_cv: dict[str, Any],
    job_posting: dict[str, Any],
    dal: Any,
    language: str = 'en',
) -> Result[list[dict[str, Any]]]:
    """Generate gap questions using LLM and prioritize by score."""
    _ = dal
    _ = language
    system_prompt = create_gap_analysis_system_prompt()
    user_prompt = create_gap_analysis_user_prompt(user_cv=user_cv, job_posting=job_posting)
    llm_client = LLMClient()

    try:
        llm_result = await _maybe_await(llm_client.generate(prompt=f'{system_prompt}\n\n{user_prompt}'))
    except TimeoutError as exc:
        return Result(success=False, error=str(exc), code=ResultCode.TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        return Result(success=False, error=str(exc), code=ResultCode.LLM_API_ERROR)

    if isinstance(llm_result, Result) and not llm_result.success:
        return llm_result

    payload = llm_result.data if isinstance(llm_result, Result) else llm_result

    try:
        questions = json.loads(payload) if isinstance(payload, str) else payload
    except Exception as exc:  # noqa: BLE001
        return Result(success=False, error=f'Failed to parse LLM response: {exc}', code=ResultCode.INTERNAL_ERROR)

    if not isinstance(questions, list):
        return Result(success=False, error='Invalid questions format', code=ResultCode.INTERNAL_ERROR)

    for question in questions:
        if 'gap_score' not in question:
            question['gap_score'] = calculate_gap_score(impact=question.get('impact', ''), probability=question.get('probability', ''))

    questions.sort(key=lambda q: q.get('gap_score', 0), reverse=True)
    questions = questions[:5]

    return Result(success=True, data=questions, code=ResultCode.GAP_QUESTIONS_GENERATED)
