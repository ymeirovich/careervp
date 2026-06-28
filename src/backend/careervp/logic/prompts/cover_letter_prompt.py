"""Cover Letter LLM prompts per COVER_LETTER_DESIGN.md:1301-1457."""

from __future__ import annotations

import json
from typing import Any

from careervp.logic.prompts.vpr_prompt import build_vpr_digest
from careervp.models.company import CompanyResearchResult
from careervp.models.cv import UserCV
from careervp.models.job import GapResponse
from careervp.models.vpr import VPR, VPRResponse


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
    vpr: VPR | VPRResponse,
    company_name: str,
    job_title: str,
    job_description: str,
    gap_responses: list[GapResponse | dict[str, Any]] | None = None,
    emphasis_areas: list[str] | None = None,
    *,
    company_research: CompanyResearchResult | None = None,
) -> str:
    """Build user prompt for cover letter generation."""
    sections: list[str] = [
        '# Company',
        f'{company_name}',
    ]

    if company_research is not None:
        sections.extend(
            [
                '# Company Research',
                _format_company_research(company_research),
            ]
        )

    sections.extend(
        [
            '# Role',
            f'{job_title}',
            '# Job Description',
            job_description.strip(),
            '# Candidate CV',
            json.dumps(build_cv_digest(cv), indent=2),
            '# VPR Summary',
            json.dumps(_build_vpr_summary(vpr), indent=2),
        ]
    )

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


def build_cv_digest(cv: UserCV) -> dict[str, Any]:
    """Build a compact CV digest for cover letter generation."""
    top_roles = [
        {
            'title': experience.role,
            'company': experience.company,
            'duration': experience.dates or experience.start_date or '',
        }
        for experience in cv.work_experience[:3]
    ]
    return {
        'name': cv.full_name,
        'summary': cv.professional_summary,
        'top_roles': top_roles,
        'key_skills': cv.skill_names()[:10],
    }


def _format_company_research(company_research: CompanyResearchResult) -> str:
    values = ', '.join(company_research.values[:5]) or 'None'
    priorities = ', '.join(company_research.strategic_priorities[:3]) or 'None'
    lines = [f'Overview: {company_research.overview}']
    if company_research.mission:
        lines.append(f'Mission: {company_research.mission}')
    lines.append(f'Values: {values}')
    lines.append(f'Strategic Priorities: {priorities}')
    return '\n'.join(lines)


def _build_vpr_summary(vpr: VPR | VPRResponse) -> dict[str, Any]:
    if isinstance(vpr, VPRResponse):
        if vpr.vpr is not None:
            return build_vpr_digest(vpr.vpr)
        return vpr.model_dump(mode='json')
    if isinstance(vpr, VPR):
        return build_vpr_digest(vpr)
    try:
        return vpr.model_dump(mode='json')
    except TypeError:
        return vpr.model_dump()
