from __future__ import annotations

import json

from careervp.logic.cv_tailoring_prompt import build_user_prompt as build_cv_tailoring_user_prompt
from careervp.logic.prompts.cover_letter_prompt import build_cv_digest
from careervp.logic.prompts.vpr_prompt import BANNED_WORDS, build_phase2_prompt, build_phase2_system_prompt, build_vpr_digest


def test_vpr_system_prompt_contains_all_required_fields() -> None:
    system_prompt = build_phase2_system_prompt()
    required_fields = [
        'metadata',
        'executive_summary',
        'overall_fit_score',
        'top_three_strengths',
        'top_three_concerns',
        'recommended_approach',
        'differentiators',
        'top_differentiators',
        'unique_strengths',
        'positioning_statement',
        'concerns_and_mitigations',
        'value_proposition',
        'primary_value',
        'elevator_pitch',
        'application_strategy',
        'ats_keywords',
        'company_insights',
        'evidence_gaps',
        'verification_summary',
    ]
    for field in required_fields:
        assert field in system_prompt


def test_vpr_user_prompt_does_not_contain_output_schema(minimal_user_cv, minimal_vpr_request) -> None:
    prompt = build_phase2_prompt(
        evidence_payload={},
        user_cv=minimal_user_cv,
        request=minimal_vpr_request,
    )
    assert 'OUTPUT SCHEMA' not in prompt
    assert 'Return only valid JSON matching the schema in the system prompt' in prompt


def test_banned_words_still_in_user_prompt(minimal_user_cv, minimal_vpr_request) -> None:
    prompt = build_phase2_prompt(
        evidence_payload={},
        user_cv=minimal_user_cv,
        request=minimal_vpr_request,
    )
    assert 'BANNED WORDS' in prompt
    assert BANNED_WORDS[0] in prompt.lower()


def test_vpr_digest_contains_required_fields(minimal_vpr) -> None:
    digest = build_vpr_digest(minimal_vpr)
    assert 'positioning_statement' in digest
    assert 'ats_keywords_primary' in digest
    assert 'top_differentiators' in digest
    assert len(digest['top_differentiators']) <= 3
    assert 'overall_fit_score' in digest
    assert 'recommended_approach' in digest


def test_vpr_digest_does_not_include_full_schema(minimal_vpr) -> None:
    digest = build_vpr_digest(minimal_vpr)
    assert 'evidence_gaps' not in digest
    assert 'concerns_and_mitigations' not in digest
    assert len(json.dumps(digest)) < 800


def test_cv_digest_contains_name_summary_and_top_roles(minimal_user_cv) -> None:
    digest = build_cv_digest(minimal_user_cv)
    assert digest['name'] == 'Jane Smith'
    assert digest['summary'] == minimal_user_cv.professional_summary
    assert len(digest['top_roles']) == 2
    assert len(digest['key_skills']) <= 10


def test_cv_tailoring_prompt_vpr_section_uses_digest(minimal_user_cv, minimal_vpr) -> None:
    output = build_cv_tailoring_user_prompt(
        cv=minimal_user_cv,
        job_description='Build systems.',
        vpr=minimal_vpr,
    )
    vpr_start = output.index('# VPR Strategic Guide')
    vpr_section = output[vpr_start:]
    assert len(vpr_section) < 1000
    assert 'positioning_statement' in vpr_section
    assert 'ats_keywords_primary' in vpr_section
