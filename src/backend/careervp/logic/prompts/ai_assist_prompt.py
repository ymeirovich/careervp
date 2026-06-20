"""Field-scoped AI-assist prompt assembly (FE-UI-046).

Composes the CACHED, invariant system preamble (per-artifact role + anti-AI
8-pattern rules from careervp/CLAUDE.md Decision 1.6 + STAR template where
applicable + output-format contract) and the per-request USER message
(current_text + server-resolved cross-artifact digests).

This module does NOT re-implement digests. It reuses the existing helpers:
  - cover_letter_prompt.build_cv_digest / _build_vpr_summary / _format_company_research
  - vpr_prompt.build_vpr_digest (transitively, via _build_vpr_summary)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from careervp.logic.prompts.cover_letter_prompt import (
    _build_vpr_summary,
    _format_company_research,
    build_cv_digest,
)
from careervp.models.company import CompanyResearchResult
from careervp.models.cv import UserCV
from careervp.models.vpr import VPR, VPRResponse

ArtifactType = Literal['gap_analysis', 'cv_tailored', 'cover_letter', 'interview_prep']

SUPPORTED_ARTIFACT_TYPES: frozenset[str] = frozenset({'gap_analysis', 'cv_tailored', 'cover_letter', 'interview_prep'})

# Upstream artifacts each artifact type depends on for a good field-scoped rewrite.
# Used by the handler to emit a precise 409 deep-link when an upstream is missing.
REQUIRED_UPSTREAM: dict[str, tuple[str, ...]] = {
    'gap_analysis': ('cv',),
    'cv_tailored': ('cv', 'vpr'),
    'cover_letter': ('vpr', 'tailored_cv', 'company_research'),
    'interview_prep': ('vpr', 'tailored_cv'),
}


@dataclass
class AssistContext:
    """Server-resolved cross-artifact context (NEVER trusted from the client)."""

    cv: UserCV | None = None
    vpr: VPR | VPRResponse | Any | None = None
    gap_responses: list[Any] = field(default_factory=list)
    company_research: CompanyResearchResult | None = None
    tailored_cv: Any | None = None
    sub_question: str | None = None


# ── Anti-AI 8-pattern framework (careervp/CLAUDE.md Decision 1.6) ──────────────
_ANTI_AI_RULES = (
    'STYLE RULES (apply to every rewrite — non-negotiable):\n'
    '1. Avoid excessive AI phrases (e.g. "in the ever-evolving landscape", '
    '"leverage", "robust", "streamline", "utilize", "cutting-edge", "synergy").\n'
    '2. Vary sentence structure and length; do not start consecutive sentences the same way.\n'
    '3. Include minor, natural transitions rather than formulaic ones '
    '("furthermore", "moreover", "in conclusion").\n'
    '4. Avoid perfect parallel structure; let the rhythm feel human.\n'
    '5. Keep every factual claim grounded in the supplied context — never invent '
    'companies, roles, dates, or metrics.\n'
    '6. Prefer concrete, quantified detail over vague assertions.\n'
    '7. Use approximations where natural ("nearly 40%" not "39.7%").\n'
    '8. Write in the first person where the original field does; preserve the '
    'document voice.'
)

_OUTPUT_CONTRACT = (
    'OUTPUT CONTRACT: Return ONLY the rewritten field content as Markdown. '
    'Do not add a preamble, explanation, headings you were not given, code fences, '
    'or meta-commentary. Output the field value and nothing else.'
)

_STAR_TEMPLATE = (
    'STAR TEMPLATE: Structure the answer as Situation, Task, Action, Result — '
    'flowing as natural prose (not labelled sections unless the field already uses them). '
    'Lead with context, state the specific challenge, describe the actions you took, '
    'and close with a concrete, quantified outcome.'
)

_ARTIFACT_ROLES: dict[str, str] = {
    'gap_analysis': (
        'You are a career-application assistant helping a candidate answer a gap-analysis '
        "sub-question. Rewrite the candidate's answer to be specific, evidence-backed, and "
        "directly responsive to the question, drawing only on the candidate's CV."
    ),
    'cv_tailored': (
        'You are a CV-tailoring assistant. Rewrite the focused CV field for impact: factual, '
        'achievement-oriented, and ATS-keyword-aware for the target role, grounded in the '
        "candidate's CV, gap responses, and value-proposition report."
    ),
    'cover_letter': (
        'You are a cover-letter assistant. Rewrite the focused field to sound natural and human, '
        "aligned to the role and company, and grounded in the candidate's gap responses, "
        'value-proposition report, tailored CV, and company research.'
    ),
    'interview_prep': (
        "You are an interview-preparation coach. Rewrite the candidate's STAR answer to be "
        'concrete and compelling, grounded in their gap responses, value-proposition report, '
        'and tailored CV.'
    ),
}


def build_system_preamble(artifact_type: str, locale: str = 'en') -> str:
    """Build the CACHED, invariant system preamble for a given artifact type.

    Stable per (artifact_type, locale): role + anti-AI 8-pattern + STAR template
    (interview_prep only) + output-format contract + locale instruction.
    """
    if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
        raise ValueError(f'Unsupported artifact_type: {artifact_type!r}')

    sections: list[str] = [_ARTIFACT_ROLES[artifact_type], _ANTI_AI_RULES]
    if artifact_type == 'interview_prep':
        sections.append(_STAR_TEMPLATE)
    sections.append(_OUTPUT_CONTRACT)

    normalized_locale = (locale or 'en').strip() or 'en'
    if normalized_locale.lower() != 'en':
        sections.append(f'LOCALE: Write the output in locale "{normalized_locale}".')

    return '\n\n'.join(sections)


def build_user_message(
    artifact_type: str,
    field_key: str,
    current_text: str,
    context: AssistContext,
) -> str:
    """Build the per-request USER message: field + current_text + resolved digests."""
    if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
        raise ValueError(f'Unsupported artifact_type: {artifact_type!r}')

    sections: list[str] = [
        '# Field To Rewrite',
        field_key,
        '# Current Text',
        current_text or '(empty)',
    ]

    if artifact_type == 'gap_analysis':
        _append_cv_digest(sections, context.cv)
        if context.sub_question:
            sections.extend(['# Sub-Question', context.sub_question])
    elif artifact_type == 'cv_tailored':
        _append_cv_digest(sections, context.cv)
        _append_gap_responses(sections, context.gap_responses)
        _append_vpr_digest(sections, context.vpr)
    elif artifact_type == 'cover_letter':
        _append_gap_responses(sections, context.gap_responses)
        _append_vpr_digest(sections, context.vpr)
        _append_tailored_cv(sections, context.tailored_cv)
        _append_company_research(sections, context.company_research)
    elif artifact_type == 'interview_prep':
        _append_gap_responses(sections, context.gap_responses)
        _append_vpr_digest(sections, context.vpr)
        _append_tailored_cv(sections, context.tailored_cv)

    return '\n\n'.join(sections)


def _append_cv_digest(sections: list[str], cv: UserCV | None) -> None:
    if cv is None:
        return
    sections.append('# Candidate CV')
    sections.append(json.dumps(build_cv_digest(cv), indent=2, ensure_ascii=False))


def _append_vpr_digest(sections: list[str], vpr: Any | None) -> None:
    if vpr is None:
        return
    sections.append('# VPR Summary')
    sections.append(json.dumps(_build_vpr_summary(vpr), indent=2, ensure_ascii=False))


def _append_gap_responses(sections: list[str], gap_responses: list[Any]) -> None:
    if not gap_responses:
        return
    serialized: list[Any] = []
    for response in gap_responses:
        if hasattr(response, 'model_dump'):
            serialized.append(response.model_dump(mode='json'))
        elif isinstance(response, dict):
            serialized.append(response)
    if serialized:
        sections.append('# Gap Responses')
        sections.append(json.dumps(serialized, indent=2, ensure_ascii=False))


def _append_company_research(sections: list[str], company_research: CompanyResearchResult | None) -> None:
    if company_research is None:
        return
    sections.append('# Company Research')
    sections.append(_format_company_research(company_research))


def _append_tailored_cv(sections: list[str], tailored_cv: Any | None) -> None:
    if tailored_cv is None:
        return
    sections.append('# Tailored CV')
    if isinstance(tailored_cv, str):
        sections.append(tailored_cv)
    elif hasattr(tailored_cv, 'model_dump'):
        sections.append(json.dumps(tailored_cv.model_dump(mode='json'), indent=2, ensure_ascii=False))
    else:
        sections.append(json.dumps(tailored_cv, indent=2, ensure_ascii=False, default=str))


__all__ = [
    'AssistContext',
    'ArtifactType',
    'SUPPORTED_ARTIFACT_TYPES',
    'REQUIRED_UPSTREAM',
    'build_system_preamble',
    'build_user_message',
]
