"""
VPR prompt builder tests (Task 04).
"""

from careervp.logic.prompts.vpr_prompt import BANNED_WORDS, build_vpr_prompt, check_anti_ai_patterns
from careervp.models.cv import ContactInfo, UserCV
from careervp.models.job import JobPosting
from careervp.models.vpr import VPRRequest


def _sample_user_cv() -> UserCV:
    return UserCV(
        user_id='user-789',
        full_name='Jordan Avery',
        language='en',
        contact_info=ContactInfo(email='jordan@example.com'),
        experience=[
            {'company': 'Nova Metrics', 'role': 'Data Lead', 'dates': '2020 – Present', 'achievements': []},
        ],
        education=[],
        certifications=[],
        skills=['Data Strategy'],
        top_achievements=[],
        raw_text='raw cv content',
        is_parsed=True,
    )


def _sample_request() -> VPRRequest:
    posting = JobPosting(
        company_name='Insight Labs',
        role_title='Head of Data',
        description='',
        responsibilities=['Lead analytics org'],
        requirements=['8+ years leadership'],
        nice_to_have=[],
        language='en',
    )
    return VPRRequest(
        application_id='app-111',
        user_id='user-789',
        job_posting=posting,
    )


class TestBuildVPRPrompt:
    def test_prompt_includes_serialized_context(self) -> None:
        prompt = build_vpr_prompt(_sample_user_cv(), _sample_request())

        assert 'Jordan Avery' in prompt  # CV facts preserved.
        assert 'Insight Labs' in prompt  # Job posting present.
        assert 'GAP ANALYSIS RESPONSES' in prompt

    def test_prompt_excludes_removed_fields(self) -> None:
        prompt = build_vpr_prompt(_sample_user_cv(), _sample_request())

        assert 'raw cv content' not in prompt  # raw_text stripped during serialization.


class TestAntiAIPatterns:
    def test_detects_banned_terms(self) -> None:
        content = f'This tries to {BANNED_WORDS[0]} outcomes and embrace synergy.'
        matches = check_anti_ai_patterns(content)

        assert BANNED_WORDS[0] in matches
        assert 'synergy' in matches
