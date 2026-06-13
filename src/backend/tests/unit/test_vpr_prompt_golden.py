"""FE-UI-033 golden tests: verify token-optimization invariants.

Tests assert structural properties after token-optimization changes:
1. VPR system prompt contains all required output field names
2. VPR user prompt no longer contains the OUTPUT SCHEMA block
3. CV Tailoring user prompt uses digest (positioning_statement, ats_keywords_primary)
4. Cover Letter user prompt uses cv digest (full_name, top 3 role titles)
5. BANNED_WORDS list remains in VPR user prompt (not moved to cached system)
"""

from __future__ import annotations

from typing import Any

import pytest

from careervp.logic.cv_tailoring_prompt import build_user_prompt as build_cv_tailoring_user_prompt
from careervp.logic.prompts.cover_letter_prompt import build_user_prompt as build_cover_letter_user_prompt
from careervp.logic.prompts.vpr_prompt import (
    BANNED_WORDS,
    build_phase2_prompt,
    build_phase2_system_prompt,
)

# All field names that must appear in the VPR system prompt (output schema invariant).
REQUIRED_VPR_FIELD_NAMES = [
    'metadata',
    'executive_summary',
    'overall_fit_score',
    'top_three_strengths',
    'top_three_concerns',
    'recommended_approach',
    'differentiators',
    'top_differentiators',
    'unique_strengths',
    'competitive_advantages',
    'positioning_statement',
    'concerns_and_mitigations',
    'likely_objections',
    'mitigation',
    'value_proposition',
    'primary_value',
    'secondary_values',
    'quantified_impact',
    'elevator_pitch',
    'application_strategy',
    'ats_keywords',
    'cv_lead_differentiator',
    'sections_to_compress',
    'company_insights',
    'evidence_gaps',
    'verification_summary',
]


@pytest.mark.unit
class TestVPRSystemPromptSchema:
    def test_all_required_field_names_in_system_prompt(self) -> None:
        system_prompt = build_phase2_system_prompt()
        missing = [field for field in REQUIRED_VPR_FIELD_NAMES if field not in system_prompt]
        assert not missing, f'Missing VPR output field names in system prompt: {missing}'

    def test_system_prompt_contains_output_schema_marker(self) -> None:
        assert 'OUTPUT SCHEMA' in build_phase2_system_prompt()

    def test_system_prompt_is_non_empty(self) -> None:
        assert len(build_phase2_system_prompt().strip()) > 200


@pytest.mark.unit
class TestVPRUserPromptSchemaAbsent:
    def test_user_prompt_does_not_contain_output_schema_block(self, minimal_user_cv: Any, minimal_vpr_request: Any) -> None:
        evidence_payload: dict[str, Any] = {
            'matches': [{'requirement': 'Python', 'evidence': '5 years', 'alignment_score': 90}],
            'uncovered_requirements': [],
            'key_skills': ['Python'],
            'experience_level': 'senior',
        }
        user_prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
        )
        assert 'OUTPUT SCHEMA' not in user_prompt, 'VPR user prompt must not contain the OUTPUT SCHEMA block — it belongs in the cached system prompt'

    def test_user_prompt_contains_banned_words_list(self, minimal_user_cv: Any, minimal_vpr_request: Any) -> None:
        evidence_payload: dict[str, Any] = {
            'matches': [],
            'uncovered_requirements': [],
            'key_skills': [],
            'experience_level': 'mid',
        }
        user_prompt = build_phase2_prompt(
            evidence_payload=evidence_payload,
            user_cv=minimal_user_cv,
            request=minimal_vpr_request,
        )
        # At least one banned word from BANNED_WORDS must appear as a constraint in the user prompt.
        found = [word for word in BANNED_WORDS if word in user_prompt]
        assert found, 'BANNED_WORDS must remain in the VPR user prompt (not moved to cached system)'


@pytest.mark.unit
class TestCVTailoringVPRDigest:
    def test_user_prompt_contains_positioning_statement_key(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        prompt = build_cv_tailoring_user_prompt(
            cv=minimal_user_cv,
            job_description='Python engineer role',
            vpr=minimal_vpr,
        )
        assert 'positioning_statement' in prompt

    def test_user_prompt_contains_ats_keywords_primary_key(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        prompt = build_cv_tailoring_user_prompt(
            cv=minimal_user_cv,
            job_description='Python engineer role',
            vpr=minimal_vpr,
        )
        assert 'ats_keywords_primary' in prompt

    def test_user_prompt_does_not_contain_full_vpr_dump(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        prompt = build_cv_tailoring_user_prompt(
            cv=minimal_user_cv,
            job_description='Python engineer role',
            vpr=minimal_vpr,
        )
        # Full model_dump would contain these deeply nested VPR-only fields;
        # the digest intentionally omits them.
        assert 'experience_mapping' not in prompt
        assert 'skills_analysis' not in prompt


@pytest.mark.unit
class TestCoverLetterCVDigest:
    def test_user_prompt_contains_candidate_name(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        prompt = build_cover_letter_user_prompt(
            cv=minimal_user_cv,
            vpr=minimal_vpr,
            company_name='SysAid',
            job_title='Staff Engineer',
            job_description='Lead platform engineering.',
        )
        assert minimal_user_cv.full_name in prompt

    def test_user_prompt_contains_top_role_titles(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        prompt = build_cover_letter_user_prompt(
            cv=minimal_user_cv,
            vpr=minimal_vpr,
            company_name='SysAid',
            job_title='Staff Engineer',
            job_description='Lead platform engineering.',
        )
        # At least the first role title must appear in the digest.
        first_exp = minimal_user_cv.work_experience[0]
        assert first_exp.role in prompt

    def test_user_prompt_does_not_contain_full_cv_dump(self, minimal_vpr: Any, minimal_user_cv: Any) -> None:
        prompt = build_cover_letter_user_prompt(
            cv=minimal_user_cv,
            vpr=minimal_vpr,
            company_name='SysAid',
            job_title='Staff Engineer',
            job_description='Lead platform engineering.',
        )
        # Digest omits raw achievements and email — full dump would include them.
        assert 'achievements' not in prompt
        assert minimal_user_cv.email not in prompt
