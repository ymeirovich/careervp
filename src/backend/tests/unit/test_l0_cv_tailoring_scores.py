"""L0.4 real unit tests for CV tailoring quality gates and persistence."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from careervp.logic.cv_tailoring import (
    KeywordMap,
    TailoredCVDraft,
    tailor_cv,
    validate_and_finalize,
)
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.cv_tailoring_models import TailoredCVResponse
from careervp.models.result import Result, ResultCode


def _sample_cv() -> UserCV:
    return UserCV(
        user_id='user-l0-4',
        cv_id='cv-l0-4',
        full_name='Jordan Candidate',
        language='en',
        contact_info=ContactInfo(email='jordan@example.com'),
        professional_summary='Cloud-focused platform engineer with delivery and leadership experience.',
        experience=[
            WorkExperience(
                company='Nimbus Labs',
                role='Senior Software Engineer',
                dates='2021 - Present',
                achievements=[
                    'Improved release reliability across services',
                    'Led migration to containerized workloads',
                ],
                technologies=['Python', 'AWS', 'Kubernetes'],
            )
        ],
        education=[],
        certifications=[],
        skills=['Python', 'AWS', 'Kubernetes', 'Leadership'],
        top_achievements=['Reduced incident rate by 30%'],
        languages=['English'],
        is_parsed=True,
    )


def _sample_keyword_map() -> KeywordMap:
    keywords = [
        'python',
        'aws',
        'kubernetes',
        'automation',
        'scalability',
        'leadership',
        'delivery',
        'reliability',
        'observability',
        'architecture',
        'security',
        'optimization',
    ]
    return KeywordMap(
        required=keywords[:6],
        preferred=keywords[6:10],
        nice_to_have=keywords[10:],
        mapped_keywords={
            'professional_summary': keywords[:5],
            'work_experience': keywords[5:10],
            'skills': keywords[10:],
        },
        keyword_categories=dict.fromkeys(keywords, 'required'),
    )


def _sample_llm_payload() -> dict[str, object]:
    return {
        'professional_summary': ('Engineering leader with deep AWS and Kubernetes delivery history, focused on measurable outcomes.'),
        'work_experience': [
            {
                'company': 'Nimbus Labs',
                'role': 'Senior Software Engineer',
                'dates': '2021 - Present',
                'achievements': [
                    (
                        'Led | In platform engineering at Nimbus Labs | Applied Python and Kubernetes automation '
                        'to release orchestration | Increased deployment reliability by 35%'
                    )
                ],
                'technologies': ['Python', 'AWS', 'Kubernetes'],
            }
        ],
        'skills': ['Python', 'AWS', 'Kubernetes', 'Leadership', 'Automation'],
        'changes_made': [{'section': 'summary', 'change_type': 'rewrite', 'description': 'Added ATS keywords'}],
        'job_description': ('Required: Python AWS Kubernetes automation scalability leadership reliability observability architecture.'),
    }


def _weak_draft() -> TailoredCVDraft:
    base = tailor_cv(_sample_cv(), _sample_keyword_map())
    assert isinstance(base, TailoredCVDraft)

    weak_cv = base.tailored_cv.model_copy(deep=True)
    weak_cv.professional_summary = ''
    weak_cv.skills = []
    for experience in weak_cv.work_experience:
        experience.achievements = ['Managed platform delivery without quantified outcomes']

    return replace(base, tailored_cv=weak_cv, preliminary_ats_score=32)


@pytest.mark.unit
def test_cv_tailoring_returns_non_null_cv_id_and_persists_with_dal() -> None:
    """Legacy tailoring path persists via DAL and returns non-null cv_id."""
    cv = _sample_cv()

    class DalStub:
        def __init__(self) -> None:
            self.saved_calls = 0
            self.saved_cv_id: str | None = None

        def check_rate_limit(self, _user_id: str) -> bool:
            return False

        def save_tailored_cv(self, *, tailored_cv: object, job_id: str | None = None) -> Result[None]:
            self.saved_calls += 1
            self.saved_cv_id = getattr(tailored_cv, 'cv_id', None)
            _ = job_id
            return Result(success=True, data=None, code=ResultCode.SUCCESS)

    dal_stub = DalStub()

    mock_llm = MagicMock()
    mock_llm.generate.return_value = _sample_llm_payload()

    result = tailor_cv(
        master_cv=cv,
        job_description=('Required: Python AWS Kubernetes automation scalability leadership reliability observability architecture.'),
        dal=dal_stub,
        llm_client=mock_llm,
    )

    assert result.success is True
    assert isinstance(result.data, TailoredCVResponse)
    assert result.data.ats_score >= 0
    assert dal_stub.saved_calls == 1
    assert dal_stub.saved_cv_id == cv.cv_id


@pytest.mark.unit
def test_cv_tailoring_ats_score_meets_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """Finalized ATS score must be at least 80 (P4: 0-100 scale)."""
    monkeypatch.setattr(
        'careervp.logic.cv_tailoring.check_anti_ai_patterns',
        lambda _text: SimpleNamespace(score=94, issues=[]),
    )
    final = validate_and_finalize(_weak_draft())
    assert final.ats_score >= 80


@pytest.mark.unit
def test_cv_tailoring_anti_ai_score_meets_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """Finalized anti-AI score must be at least 90 (P4: 0-100 scale)."""
    monkeypatch.setattr(
        'careervp.logic.cv_tailoring.check_anti_ai_patterns',
        lambda _text: SimpleNamespace(score=93, issues=[]),
    )
    final = validate_and_finalize(_weak_draft())
    assert final.metadata.get('anti_ai_score', 0) >= 90


@pytest.mark.unit
def test_cv_tailoring_self_correction_triggers_on_low_score(monkeypatch: pytest.MonkeyPatch) -> None:
    """Low initial anti-AI score triggers at least one self-correction iteration."""
    call_count = {'value': 0}

    def _low_then_high(_text: str) -> SimpleNamespace:
        call_count['value'] += 1
        if call_count['value'] == 1:
            return SimpleNamespace(score=81, issues=['templated language'])
        return SimpleNamespace(score=92, issues=[])

    monkeypatch.setattr('careervp.logic.cv_tailoring.check_anti_ai_patterns', _low_then_high)
    final = validate_and_finalize(_weak_draft())
    assert final.iterations >= 1


@pytest.mark.unit
def test_cv_tailoring_max_3_correction_iterations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Self-correction loop is bounded to 3 attempts."""
    weak_draft = _weak_draft()
    repair_calls = {'count': 0}

    def _fake_repair(
        _master_cv: UserCV,
        _keyword_map: KeywordMap,
        _feedback: str | None = None,
    ) -> TailoredCVDraft:
        repair_calls['count'] += 1
        return weak_draft

    monkeypatch.setattr('careervp.logic.cv_tailoring.calculate_ats_score', lambda _cv, _map: 55)
    monkeypatch.setattr(
        'careervp.logic.cv_tailoring.check_anti_ai_patterns',
        lambda _text: SimpleNamespace(score=96, issues=[]),
    )
    monkeypatch.setattr('careervp.logic.cv_tailoring.tailor_cv', _fake_repair)

    final = validate_and_finalize(weak_draft)
    assert final.iterations == 3
    assert repair_calls['count'] == 3
