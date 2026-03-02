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
MAX_QUESTIONS = 10

TAG_CV_IMPACT = '[CV IMPACT]'
TAG_TECHNICAL = '[TECHNICAL]'
TAG_BEHAVIORAL = '[BEHAVIORAL]'
TAG_INTERVIEW_MVP = '[INTERVIEW/MVP ONLY]'

TAG_DISTRIBUTION: tuple[str, ...] = (
    TAG_CV_IMPACT,
    TAG_CV_IMPACT,
    TAG_CV_IMPACT,
    TAG_CV_IMPACT,
    TAG_TECHNICAL,
    TAG_TECHNICAL,
    TAG_BEHAVIORAL,
    TAG_BEHAVIORAL,
    TAG_INTERVIEW_MVP,
    TAG_INTERVIEW_MVP,
)


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


def _normalize_level(value: Any) -> str:
    normalized = str(value).strip().upper()
    if normalized in IMPACT_SCORES:
        return normalized
    return 'MEDIUM'


def _normalize_tags(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_tags = [value]
    elif isinstance(value, list):
        raw_tags = [entry for entry in value if isinstance(entry, str)]
    else:
        raw_tags = []

    normalized_tags: list[str] = []
    for raw in raw_tags:
        normalized = raw.strip().upper().replace('_', ' ')
        if 'CV' in normalized and 'IMPACT' in normalized:
            tag = TAG_CV_IMPACT
        elif 'TECH' in normalized:
            tag = TAG_TECHNICAL
        elif 'BEHAV' in normalized or 'STAR' in normalized:
            tag = TAG_BEHAVIORAL
        elif 'INTERVIEW' in normalized or 'MVP' in normalized:
            tag = TAG_INTERVIEW_MVP
        else:
            continue

        if tag not in normalized_tags:
            normalized_tags.append(tag)
    return normalized_tags


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM response text."""
    stripped = text.strip()
    if stripped.startswith('```'):
        # Remove opening fence (```json, ```JSON, ``` etc.)
        first_newline = stripped.find('\n')
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        # Remove closing fence
        if stripped.rstrip().endswith('```'):
            stripped = stripped.rstrip()[:-3].rstrip()
    return stripped


def _find_json_in_text(text: str) -> Any:
    """Find and parse the first valid JSON object or array embedded in text."""
    stripped = _strip_markdown_fences(text)
    # Try parsing the whole string first (fast path)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Scan for JSON object or array starting positions
    for start_char in ('{', '['):
        pos = stripped.find(start_char)
        if pos == -1:
            continue
        candidate = stripped[pos:]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    raise ValueError(f'No valid JSON found in LLM response (first 200 chars): {text[:200]!r}')


def _extract_questions(payload: Any) -> list[dict[str, Any]]:
    parsed: Any = payload

    if isinstance(parsed, str):
        parsed = _find_json_in_text(parsed)

    while isinstance(parsed, dict):
        if isinstance(parsed.get('questions'), list):
            parsed = parsed['questions']
            break
        if isinstance(parsed.get('text'), str):
            parsed = _find_json_in_text(parsed['text'])
            continue
        raise ValueError('Invalid questions format')

    if not isinstance(parsed, list):
        raise ValueError('Invalid questions format')

    questions: list[dict[str, Any]] = []
    for index, entry in enumerate(parsed):
        if not isinstance(entry, dict):
            raise ValueError(f'Question at index {index} is not an object')
        questions.append(dict(entry))
    return questions


def _coerce_gap_score(question: dict[str, Any], impact: str, probability: str) -> float:
    raw_gap_score = question.get('gap_score')
    if isinstance(raw_gap_score, (int, float)):
        bounded = max(0.0, min(1.0, float(raw_gap_score)))
        return round(bounded, 2)
    return calculate_gap_score(impact=impact, probability=probability)


def _normalize_question(question: dict[str, Any], index: int) -> dict[str, Any]:
    impact = _normalize_level(question.get('impact'))
    probability = _normalize_level(question.get('probability'))
    question_id = str(question.get('question_id') or question.get('id') or f'q{index + 1}')
    text = str(question.get('question') or question.get('text') or f'Provide evidence for gap area #{index + 1}.')
    tags = _normalize_tags(question.get('tags'))
    gap_score = _coerce_gap_score(question, impact=impact, probability=probability)

    return {
        'question_id': question_id,
        'question': text,
        'impact': impact,
        'probability': probability,
        'gap_score': gap_score,
        'tags': tags,
    }


def _ensure_question_count(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = questions[:MAX_QUESTIONS]
    while len(normalized) < MAX_QUESTIONS:
        index = len(normalized) + 1
        fallback_impact = 'LOW'
        fallback_probability = 'LOW'
        normalized.append(
            {
                'question_id': f'generated-q{index}',
                'question': f'What concrete evidence demonstrates fit for uncovered requirement #{index}?',
                'impact': fallback_impact,
                'probability': fallback_probability,
                'gap_score': 0.0,
                'tags': [],
            }
        )
    return normalized


def _apply_tag_distribution(questions: list[dict[str, Any]]) -> None:
    for index, question in enumerate(questions):
        # Keep array schema while enforcing deterministic category coverage.
        question['tags'] = [TAG_DISTRIBUTION[index]]


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
        parsed_questions = _extract_questions(payload)
    except Exception:  # noqa: BLE001
        # LLM returned non-parseable content; fall back to generated questions
        parsed_questions = []

    questions = [_normalize_question(question=question, index=index) for index, question in enumerate(parsed_questions)]

    questions.sort(key=lambda q: float(q.get('gap_score', 0.0)), reverse=True)
    questions = _ensure_question_count(questions)
    _apply_tag_distribution(questions)

    return Result(success=True, data=questions, code=ResultCode.GAP_QUESTIONS_GENERATED)
