"""Unit tests for FE-UI-046 AI-assist prompt assembly (AC-002..AC-005)."""

from __future__ import annotations

from typing import Any

import pytest

from careervp.logic.prompts.ai_assist_prompt import (
    AssistContext,
    build_system_preamble,
    build_user_message,
)
from careervp.models.company import CompanyResearchResult, ResearchSource
from careervp.models.cv import UserCV


class _VprStub:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, mode: str = 'json') -> dict[str, Any]:
        _ = mode
        return self._payload


def _cv() -> UserCV:
    return UserCV.model_validate(
        {
            'user_id': 'user-1',
            'full_name': 'Ada Lovelace',
            'professional_summary': 'Engineer with a decade of distributed-systems work.',
            'work_experience': [
                {'company': 'Acme', 'role': 'Staff Engineer', 'dates': '2019-Present'},
            ],
            'skills': ['Python', 'AWS'],
        }
    )


def _vpr() -> _VprStub:
    return _VprStub({'positioning_statement': 'Rare reliability leader', 'ats_keywords_primary': ['AWS']})


def _company_research() -> CompanyResearchResult:
    return CompanyResearchResult(
        company_name='TechCorp',
        overview='A cloud platform company.',
        values=['ownership'],
        source=ResearchSource.WEBSITE_SCRAPE,
    )


def _gap_responses() -> list[dict[str, Any]]:
    return [{'question_id': 'gap-1', 'question': 'Kubernetes?', 'answer': 'Ran 50-node clusters.'}]


# ── build_system_preamble (AC-005) ────────────────────────────────────────────


def test_preamble_includes_anti_ai_rules_for_every_artifact() -> None:
    for artifact_type in ('gap_analysis', 'cv_tailored', 'cover_letter', 'interview_prep'):
        preamble = build_system_preamble(artifact_type, 'en')
        assert 'STYLE RULES' in preamble
        assert 'Vary sentence structure' in preamble
        assert 'OUTPUT CONTRACT' in preamble


def test_preamble_includes_star_template_only_for_interview_prep() -> None:
    assert 'STAR TEMPLATE' in build_system_preamble('interview_prep', 'en')
    assert 'STAR TEMPLATE' not in build_system_preamble('cover_letter', 'en')


def test_preamble_cv_tailored_mentions_ats_and_impact() -> None:
    preamble = build_system_preamble('cv_tailored', 'en')
    assert 'ATS' in preamble
    assert 'impact' in preamble.lower()


def test_preamble_adds_locale_only_when_non_english() -> None:
    assert 'LOCALE' in build_system_preamble('cover_letter', 'he')
    assert 'LOCALE' not in build_system_preamble('cover_letter', 'en')


def test_preamble_rejects_unknown_artifact_type() -> None:
    with pytest.raises(ValueError):
        build_system_preamble('unknown', 'en')


# ── build_user_message per artifact (AC-002, AC-003, AC-004) ──────────────────


def test_gap_analysis_message_has_cv_digest_and_subquestion_only() -> None:
    context = AssistContext(cv=_cv(), sub_question='Describe a leadership gap.')
    message = build_user_message('gap_analysis', 'answer', 'my current text', context)
    assert '# Field To Rewrite' in message
    assert 'my current text' in message
    assert '# Candidate CV' in message
    assert '# Sub-Question' in message
    assert '# VPR Summary' not in message
    assert '# Gap Responses' not in message


def test_cv_tailored_message_has_cv_gap_and_vpr() -> None:
    context = AssistContext(cv=_cv(), gap_responses=_gap_responses(), vpr=_vpr())
    message = build_user_message('cv_tailored', 'summary', 'text', context)
    assert '# Candidate CV' in message
    assert '# Gap Responses' in message
    assert '# VPR Summary' in message
    assert 'positioning_statement' in message


def test_interview_prep_message_has_gap_vpr_tailored_cv() -> None:
    context = AssistContext(gap_responses=_gap_responses(), vpr=_vpr(), tailored_cv='## Tailored CV body')
    message = build_user_message('interview_prep', 'q1', 'star draft', context)
    assert '# Gap Responses' in message
    assert '# VPR Summary' in message
    assert '# Tailored CV' in message
    assert 'star draft' in message


def test_cover_letter_message_has_all_four_contexts() -> None:
    context = AssistContext(
        gap_responses=_gap_responses(),
        vpr=_vpr(),
        tailored_cv='tailored',
        company_research=_company_research(),
    )
    message = build_user_message('cover_letter', 'body', 'draft', context)
    assert '# Gap Responses' in message
    assert '# VPR Summary' in message
    assert '# Tailored CV' in message
    assert '# Company Research' in message
    assert 'A cloud platform company.' in message


def test_user_message_omits_absent_optional_sections() -> None:
    message = build_user_message('cv_tailored', 'summary', 'text', AssistContext(cv=_cv()))
    assert '# Gap Responses' not in message
    assert '# VPR Summary' not in message
