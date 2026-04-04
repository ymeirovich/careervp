"""Cover letter generation logic."""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from careervp.logic.fvs_validator import check_anti_ai_patterns
from careervp.logic.llm_client import LLMClient
from careervp.logic.prompts.cover_letter_prompt import build_system_prompt, build_user_prompt
from careervp.models.cover_letter import (
    CoverLetter,
    CoverLetterParagraph,
    CoverLetterRequest,
    CoverLetterResponse,
)
from careervp.models.cv import UserCV
from careervp.models.job import GapResponse
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPRResponse

WORD_COUNT_TARGETS = {'short': 220, 'standard': 300, 'long': 350}
MAX_WORD_COUNT = 350
MIN_PARAGRAPH_COUNT = 2
MAX_PARAGRAPH_COUNT = 3
ANTI_AI_MIN_SCORE = 90  # 0-100 scale (P4)
DISALLOWED_OUTPUT_MARKERS = (
    'company for ',
    'role for ',
    'job description for ',
    'referenced as placeholders rather than actual content',
    'unable to generate a tailored cover letter',
    'please share the actual job posting information',
    'i appreciate your request',
)
BULLET_LIST_PATTERN = re.compile(r'^\s*(?:[-*]\s+|\d+\.\s+)')


async def _maybe_await(value: Any) -> Any:
    if asyncio.iscoroutine(value):
        return await value
    return value


async def generate_cover_letter(  # noqa: C901
    request: CoverLetterRequest,
    user_cv: UserCV,
    vpr: VPRResponse,
    gap_responses: list[GapResponse | dict[str, Any]] | None = None,
) -> Result[CoverLetterResponse]:
    """Generate a personalised cover letter."""
    start_time = time.perf_counter()

    tone = 'professional'
    length = 'standard'
    if request.options:
        tone = request.options.tone
        length = request.options.length

    word_count_target = WORD_COUNT_TARGETS.get(length, 350)

    system_prompt = build_system_prompt(tone=tone, word_count_target=word_count_target)
    user_prompt = build_user_prompt(
        cv=user_cv,
        vpr=vpr,
        company_name=request.company_name,
        job_title=request.job_title,
        job_description=request.job_description,
        gap_responses=gap_responses,
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

    # LLMClient.generate returns dict[str, Any] - extract text content
    raw_text: str
    if isinstance(llm_result, dict):
        raw_text = str(llm_result.get('text', llm_result.get('completion', json.dumps(llm_result))))
    elif isinstance(llm_result, str):
        raw_text = llm_result
    else:
        raw_text = str(llm_result)

    try:
        cover_letter = _parse_cover_letter_response(raw_text, request)
    except ValueError as exc:
        return Result(
            success=False,
            error=f'Failed to parse cover letter: {exc}',
            code=ResultCode.INTERNAL_ERROR,
        )

    # Validate word count
    if cover_letter.word_count > MAX_WORD_COUNT:
        return Result(
            success=False,
            error=f'Cover letter exceeds {MAX_WORD_COUNT} word limit ({cover_letter.word_count} words)',
            code=ResultCode.FVS_VALIDATION_FAILED,
        )
    paragraph_count = len([paragraph for paragraph in cover_letter.paragraphs if paragraph.content.strip()])
    if paragraph_count < MIN_PARAGRAPH_COUNT or paragraph_count > MAX_PARAGRAPH_COUNT:
        return Result(
            success=False,
            error=(f'Cover letter must contain {MIN_PARAGRAPH_COUNT}-{MAX_PARAGRAPH_COUNT} paragraphs (received {paragraph_count})'),
            code=ResultCode.FVS_VALIDATION_FAILED,
        )
    content_violation = _detect_output_content_violation(cover_letter.full_text)
    if content_violation:
        return Result(
            success=False,
            error=content_violation,
            code=ResultCode.FVS_VALIDATION_FAILED,
        )

    anti_ai_assessment = check_anti_ai_patterns(cover_letter.full_text)
    if anti_ai_assessment.score < ANTI_AI_MIN_SCORE:
        issues = '; '.join(anti_ai_assessment.issues) if anti_ai_assessment.issues else 'No issue details available.'
        return Result(
            success=False,
            error=(
                f'Anti-AI score {anti_ai_assessment.score:.2f} below threshold {ANTI_AI_MIN_SCORE:.1f}. '
                f'Regenerate cover letter with more natural language. Issues: {issues}'
            ),
            code=ResultCode.FVS_VALIDATION_FAILED,
        )

    generation_time_ms = int((time.perf_counter() - start_time) * 1000)

    response = CoverLetterResponse(
        success=True,
        cover_letter=cover_letter,
        generation_time_ms=generation_time_ms,
    )

    return Result(success=True, data=response, code=ResultCode.COVER_LETTER_GENERATED)


def _parse_cover_letter_response(raw_text: str, request: CoverLetterRequest) -> CoverLetter:
    """Parse LLM output into CoverLetter model."""
    # Strip code block markers if present
    cleaned = raw_text.strip()
    if cleaned.startswith('```'):
        first_nl = cleaned.find('\n')
        if first_nl != -1:
            cleaned = cleaned[first_nl + 1 :]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    paragraphs: list[CoverLetterParagraph] = []
    full_text = cleaned

    try:
        payload = json.loads(cleaned)
        full_text = payload.get('full_text', payload.get('cover_letter', cleaned))

        para_types: list[str] = ['hook', 'proof_points', 'close']
        raw_paragraphs = payload.get('paragraphs', [])
        for i, para in enumerate(raw_paragraphs[:MAX_PARAGRAPH_COUNT]):
            if isinstance(para, dict):
                p_type = para.get('type', para_types[i] if i < len(para_types) else 'hook')
                content = para.get('content', '')
            else:
                p_type = para_types[i] if i < len(para_types) else 'hook'
                content = str(para)
            paragraphs.append(
                CoverLetterParagraph(
                    type=p_type,
                    content=content,
                    word_count=len(content.split()),
                )
            )
    except (json.JSONDecodeError, ValueError):
        # Treat as plain text - split into 3 paragraphs
        parts = [p.strip() for p in full_text.split('\n\n') if p.strip()]
        plain_para_types: list[Literal['hook', 'proof_points', 'close']] = ['hook', 'proof_points', 'close']
        for i, part in enumerate(parts[:MAX_PARAGRAPH_COUNT]):
            p_type = plain_para_types[i] if i < len(plain_para_types) else 'hook'
            paragraphs.append(
                CoverLetterParagraph(
                    type=p_type,
                    content=part,
                    word_count=len(part.split()),
                )
            )
    paragraphs = _normalize_paragraph_count(full_text=full_text, paragraphs=paragraphs)
    if paragraphs:
        full_text = '\n\n'.join(paragraph.content.strip() for paragraph in paragraphs if paragraph.content.strip())

    word_count = len(full_text.split())
    tone = 'professional'
    if request.options:
        tone = request.options.tone

    return CoverLetter(
        cover_letter_id=str(uuid.uuid4()),
        user_id=request.user_id,
        job_id=request.job_id,
        cv_id=request.cv_id,
        vpr_id=request.vpr_id,
        full_text=full_text,
        paragraphs=paragraphs,
        word_count=word_count,
        tone=tone,
        created_at=datetime.now(timezone.utc),
        version=1,
    )


def _normalize_paragraph_count(
    full_text: str,
    paragraphs: list[CoverLetterParagraph],
) -> list[CoverLetterParagraph]:
    """Normalize parsed cover letter paragraphs to required 2-3 count."""
    cleaned = [paragraph for paragraph in paragraphs if paragraph.content.strip()]
    if len(cleaned) > MAX_PARAGRAPH_COUNT:
        return cleaned[:MAX_PARAGRAPH_COUNT]
    if MIN_PARAGRAPH_COUNT <= len(cleaned) <= MAX_PARAGRAPH_COUNT:
        return cleaned

    source_text = full_text.strip()
    if not source_text and cleaned:
        source_text = cleaned[0].content.strip()
    split_parts = _split_into_two_paragraphs(source_text)
    if len(split_parts) == 2:
        return [
            CoverLetterParagraph(type='hook', content=split_parts[0], word_count=len(split_parts[0].split())),
            CoverLetterParagraph(type='proof_points', content=split_parts[1], word_count=len(split_parts[1].split())),
        ]
    return cleaned[:MAX_PARAGRAPH_COUNT]


def _split_into_two_paragraphs(text: str) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []

    sentences = [part.strip() for part in re.split(r'(?<=[.!?])\s+', normalized) if part.strip()]
    if len(sentences) >= 2:
        midpoint = max(1, len(sentences) // 2)
        first = ' '.join(sentences[:midpoint]).strip()
        second = ' '.join(sentences[midpoint:]).strip()
        if first and second:
            return [first, second]

    words = normalized.split()
    if len(words) >= 20:
        midpoint = len(words) // 2
        first = ' '.join(words[:midpoint]).strip()
        second = ' '.join(words[midpoint:]).strip()
        if first and second:
            return [first, second]
    return []


def _detect_output_content_violation(cover_letter_text: str) -> str | None:
    lowered = cover_letter_text.lower()
    for marker in DISALLOWED_OUTPUT_MARKERS:
        if marker in lowered:
            return f'Cover letter contains disallowed placeholder/meta content: "{marker}"'

    for line in cover_letter_text.splitlines():
        if BULLET_LIST_PATTERN.match(line):
            return 'Cover letter contains bullet-list formatting, which is not allowed'
    return None
