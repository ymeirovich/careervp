"""Unit tests for interview prep prompt architecture input alignment.

Spec: INTERVIEW_PREP_003 — AC-IP-301
Validates that build_user_prompt includes all architecture-required
section headers from section 3.7:
  cv_facts, job_requirements, vpr_differentiators, gap_responses,
  company_research, language.
"""

from __future__ import annotations

from typing import Any

from careervp.logic.prompts.interview_prep_prompt import build_system_prompt, build_user_prompt

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _cv_facts() -> dict[str, Any]:
    return {
        'professional_summary': 'Senior engineer with 10 years in distributed systems.',
        'skills': ['Python', 'AWS', 'DynamoDB'],
        'experience': [
            {'title': 'Staff Engineer', 'company': 'Acme Corp', 'description': 'Led platform reliability'},
        ],
    }


def _job_requirements() -> dict[str, Any]:
    return {
        'title': 'Principal Engineer',
        'required_skills': ['Python', 'AWS'],
        'description': 'Lead cloud-native platform engineering.',
    }


def _vpr_differentiators() -> list[str]:
    return [
        'Unique distributed systems expertise',
        'Track record of 40% latency reduction',
        'Cross-functional leadership at scale',
    ]


def _vpr_data() -> dict[str, Any]:
    return {'vpr_id': 'vpr-001', 'executive_summary': 'Strong candidate for infrastructure roles.'}


def _gap_responses() -> list[dict[str, Any]]:
    return [
        {'question_id': 'gap-001', 'question': 'Experience with Kubernetes?', 'response': 'Managed 50+ node clusters.'},
    ]


def _company_research() -> dict[str, Any]:
    return {'company_name': 'TechCorp', 'culture': 'Engineering-driven', 'recent_news': 'Series D funding.'}


# ---------------------------------------------------------------------------
# Tests — architecture section headers present in prompt
# ---------------------------------------------------------------------------


def test_prompt_contains_cv_facts_section() -> None:
    """Prompt includes # CV Facts section when cv_facts provided."""
    prompt = build_user_prompt(
        vpr_data=_vpr_data(),
        cv_facts=_cv_facts(),
    )
    assert '# CV Facts' in prompt
    assert 'professional_summary' in prompt


def test_prompt_contains_job_requirements_section() -> None:
    """Prompt includes # Job Requirements section when job_requirements provided."""
    prompt = build_user_prompt(
        vpr_data=_vpr_data(),
        job_requirements=_job_requirements(),
    )
    assert '# Job Requirements' in prompt
    assert 'Principal Engineer' in prompt


def test_prompt_contains_vpr_differentiators_section() -> None:
    """Prompt includes # VPR Differentiators section when differentiators provided."""
    prompt = build_user_prompt(
        vpr_data=_vpr_data(),
        vpr_differentiators=_vpr_differentiators(),
    )
    assert '# VPR Differentiators' in prompt
    assert 'distributed systems expertise' in prompt


def test_prompt_contains_vpr_summary_section() -> None:
    """Prompt always includes # VPR Summary section."""
    prompt = build_user_prompt(vpr_data=_vpr_data())
    assert '# VPR Summary' in prompt
    assert 'vpr-001' in prompt


def test_prompt_contains_gap_responses_section() -> None:
    """Prompt includes # Gap Responses section when gap_responses provided."""
    prompt = build_user_prompt(
        vpr_data=_vpr_data(),
        gap_responses=_gap_responses(),
    )
    assert '# Gap Responses' in prompt
    assert 'Kubernetes' in prompt


def test_prompt_contains_company_research_section() -> None:
    """Prompt includes # Company Research section when company_research provided."""
    prompt = build_user_prompt(
        vpr_data=_vpr_data(),
        company_research=_company_research(),
    )
    assert '# Company Research' in prompt
    assert 'TechCorp' in prompt


def test_prompt_contains_all_architecture_sections() -> None:
    """Prompt with all context inputs contains every architecture-required section."""
    prompt = build_user_prompt(
        vpr_data=_vpr_data(),
        cv_facts=_cv_facts(),
        job_requirements=_job_requirements(),
        vpr_differentiators=_vpr_differentiators(),
        gap_responses=_gap_responses(),
        company_research=_company_research(),
        language='en',
        question_count=10,
    )
    required_sections = [
        '# CV Facts',
        '# Job Requirements',
        '# VPR Differentiators',
        '# VPR Summary',
        '# Gap Responses',
        '# Company Research',
    ]
    for section in required_sections:
        assert section in prompt, f'Missing required prompt section: {section!r}'


def test_prompt_language_section_added_for_non_english() -> None:
    """Non-English language produces a # Language section."""
    prompt = build_user_prompt(vpr_data=_vpr_data(), language='he')
    assert '# Language' in prompt
    assert 'he' in prompt


def test_prompt_language_section_omitted_for_english() -> None:
    """English (default) does NOT add a # Language section."""
    prompt = build_user_prompt(vpr_data=_vpr_data(), language='en')
    assert '# Language' not in prompt


def test_prompt_target_includes_question_count() -> None:
    """Prompt target section reflects the requested question count."""
    prompt = build_user_prompt(vpr_data=_vpr_data(), question_count=12)
    assert '# Target' in prompt
    assert '12' in prompt


def test_prompt_omits_absent_optional_sections() -> None:
    """Prompt without optional context does not produce empty section headers."""
    prompt = build_user_prompt(vpr_data=_vpr_data())
    for absent_section in ('# CV Facts', '# Job Requirements', '# VPR Differentiators', '# Gap Responses', '# Company Research', '# Language'):
        assert absent_section not in prompt, f'Unexpected empty section: {absent_section!r}'


def test_prompt_focus_areas_included() -> None:
    """Focus areas appear in prompt when provided."""
    prompt = build_user_prompt(
        vpr_data=_vpr_data(),
        focus_areas=['technical', 'behavioral'],
    )
    assert '# Focus Areas' in prompt
    assert 'technical' in prompt
    assert 'behavioral' in prompt


def test_system_prompt_grounds_answers_in_cv_facts() -> None:
    """System prompt rule instructs model to ground answers in CV facts."""
    system_prompt = build_system_prompt()
    assert 'CV facts' in system_prompt
