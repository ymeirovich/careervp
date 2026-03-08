"""Cover Letter LLM prompts per COVER_LETTER_DESIGN.md:1301-1457."""

from __future__ import annotations

import json
from typing import Any

from careervp.models.cv import UserCV
from careervp.models.job import GapResponse
from careervp.models.vpr import VPRResponse


def build_system_prompt(tone: str, word_count_target: int) -> str:
    """Build system prompt for cover letter generation."""
    constrained_target = min(max(word_count_target, 180), 350)
    return (
        'You are a cover letter generation assistant.\n'
        'Produce a natural, human-sounding cover letter tailored to the role.\n'
        'Constraints:\n'
        f'- Tone: {tone}\n'
        f'- Target length: ~{constrained_target} words; hard max 350 words (one page).\n'
        '- Use exactly 2 or 3 paragraphs (never 1, never more than 3).\n'
        '- No bullet lists, section headers, or meta-commentary in the final letter.\n'
        '- Preserve factual accuracy (names, dates, roles, companies).\n'
        '- Avoid generic, AI-sounding language.\n'
    )


def build_user_prompt(
    cv: UserCV,
    vpr: VPRResponse,
    company_name: str,
    job_title: str,
    job_description: str,
    gap_responses: list[GapResponse | dict[str, Any]] | None = None,
    emphasis_areas: list[str] | None = None,
) -> str:
    """Build user prompt for cover letter generation."""
    sections: list[str] = [
        '# Company',
        f'{company_name}',
        '# Role',
        f'{job_title}',
        '# Job Description',
        job_description.strip(),
        '# Candidate CV',
        json.dumps(cv.model_dump(mode='json'), indent=2),
        '# VPR Summary',
        json.dumps(vpr.model_dump(mode='json'), indent=2),
    ]

    if gap_responses:
        sections.append('# Gap Responses')
        sections.append(json.dumps(_dump_gap_responses(gap_responses), indent=2))

    if emphasis_areas:
        sections.append('# Emphasis Areas')
        sections.append(', '.join(emphasis_areas))

    return '\n\n'.join(sections)


def _dump_gap_responses(gap_responses: list[GapResponse | dict[str, Any]]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for response in gap_responses:
        if isinstance(response, GapResponse):
            serialized.append(response.model_dump(mode='json'))
        elif isinstance(response, dict):
            serialized.append(response)
    return serialized
