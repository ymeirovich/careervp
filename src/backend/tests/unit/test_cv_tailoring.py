"""Unit tests for the 3-step CV tailoring pipeline."""

from __future__ import annotations

from dataclasses import replace

from careervp.logic.cv_tailoring import (
    TailoredCVDraft,
    analyze_and_map_keywords,
    calculate_ats_score,
    tailor_cv,
    validate_and_finalize,
    validate_star_bullet,
    validate_star_format,
)
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.job import JobPosting


def _sample_cv() -> UserCV:
    return UserCV(
        user_id='user-001',
        cv_id='cv-001',
        full_name='Alex Candidate',
        language='en',
        contact_info=ContactInfo(email='alex@example.com'),
        professional_summary='Product-focused engineering leader with cloud delivery experience.',
        experience=[
            WorkExperience(
                company='Nimbus Labs',
                role='Senior Software Engineer',
                dates='2021 - Present',
                achievements=[
                    'Improved deployment reliability across platform services',
                    'Led migration to cloud-native microservices',
                ],
                technologies=['Python', 'AWS', 'Kubernetes'],
            )
        ],
        education=[],
        certifications=[],
        skills=['Python', 'AWS', 'Kubernetes', 'Leadership'],
        top_achievements=['Increased release velocity by 30%'],
        languages=['English'],
        is_parsed=True,
    )


def _sample_job() -> JobPosting:
    return JobPosting(
        company_name='Acme Cloud',
        role_title='Senior Platform Engineer',
        description=(
            'Lead cloud platform reliability, drive microservices adoption, and optimize deployment workflows for enterprise SaaS products.'
        ),
        responsibilities=[
            'Build and maintain CI/CD pipelines for distributed services',
            'Improve observability and incident response',
            'Mentor engineers and lead architecture reviews',
        ],
        requirements=[
            'Strong Python development experience',
            'Hands-on AWS and Kubernetes production expertise',
            'Experience with Terraform, automation, and scalability initiatives',
            'Excellent communication and stakeholder management',
        ],
        nice_to_have=[
            'Experience with platform security and compliance',
            'Knowledge of SRE best practices',
            'Background in performance tuning and cost optimization',
        ],
        language='en',
    )


def test_keyword_extraction_finds_12_to_18_keywords() -> None:
    keyword_map = analyze_and_map_keywords(_sample_cv(), _sample_job())
    assert 12 <= len(keyword_map.all_keywords) <= 18


def test_ats_scoring_returns_numeric_score() -> None:
    cv = _sample_cv()
    keyword_map = analyze_and_map_keywords(cv, _sample_job())
    draft = tailor_cv(cv, keyword_map)
    assert isinstance(draft, TailoredCVDraft)

    score = calculate_ats_score(draft.tailored_cv, keyword_map)
    assert isinstance(score, float)
    assert 0.0 <= score <= 10.0


def test_self_correction_iterates_max_3_times() -> None:
    cv = _sample_cv()
    keyword_map = analyze_and_map_keywords(cv, _sample_job())
    draft = tailor_cv(cv, keyword_map)
    assert isinstance(draft, TailoredCVDraft)

    weak_cv = draft.tailored_cv.model_copy(deep=True)
    weak_cv.professional_summary = ''
    weak_cv.skills = []
    for experience in weak_cv.work_experience:
        experience.achievements = ['Managed migration efforts without quantified result']

    weak_draft = replace(draft, tailored_cv=weak_cv, preliminary_ats_score=3.5)
    final = validate_and_finalize(weak_draft)

    assert final.iterations <= 3
    assert final.ats_score >= 8.0
    for iteration in final.iteration_history:
        assert iteration['improvement'] >= 0.5


def test_star_format_validation_accepts_valid_bullets() -> None:
    bullets = [
        'Led | In Platform Engineering at Nimbus Labs | Applied Kubernetes automation to release workflows | Increased deployment reliability by 35%',
        'Optimized | In CI/CD operations at Nimbus Labs | Applied Python tooling to test orchestration | Reduced pipeline duration by 22%',
    ]
    assert validate_star_format(bullets) is True
    assert all(validate_star_bullet(bullet) for bullet in bullets)


def test_star_format_validation_rejects_invalid_bullets() -> None:
    bullets = [
        'Led platform migration and improved reliability',
        'Built | Context only | Action only | Result without metric',
    ]
    assert validate_star_format(bullets) is False
    assert validate_star_bullet(bullets[0]) is False
    assert validate_star_bullet(bullets[1]) is False
